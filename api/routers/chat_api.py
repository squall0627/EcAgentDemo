import httpx
from fastapi import APIRouter, HTTPException, Depends, Query, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm.attributes import flag_modified
from db.database import get_db
from services.conversation_service import ConversationService
from services.voice_service import VoiceService
from services.image_service import ImageService
from db.models.conversation_history import ConversationHistory
from utils.langfuse_handler import get_global_langfuse_handler
import datetime
import os
import uuid

router = APIRouter()

# Langfuseハンドラーを取得（既存の初期化済みクライアントを使用）
langfuse_handler = get_global_langfuse_handler()

# 一時ファイル保存用のディレクトリ
TEMP_UPLOAD_DIR = "temp_uploads"

# 一時ファイル管理用のヘルパー関数
def ensure_temp_dir():
    """一時ディレクトリが存在することを確認"""
    if not os.path.exists(TEMP_UPLOAD_DIR):
        os.makedirs(TEMP_UPLOAD_DIR)

def save_temp_file(file_data: bytes, filename: str, session_id: str, user_id: str) -> str:
    """
    一時ファイルを保存し、ファイルIDを返す

    Args:
        file_data: ファイルデータ
        filename: 元のファイル名
        session_id: セッションID
        user_id: ユーザーID

    Returns:
        ファイルID
    """
    ensure_temp_dir()

    # ユニークなファイルIDを生成
    file_id = str(uuid.uuid4())

    # ファイル拡張子を保持
    file_extension = ""
    if "." in filename:
        file_extension = "." + filename.split(".")[-1]

    # 一時ファイルパスを生成（ユーザーID、セッションID、ファイルIDを含む）
    temp_filename = f"{user_id}_{session_id}_{file_id}{file_extension}"
    temp_filepath = os.path.join(TEMP_UPLOAD_DIR, temp_filename)

    # ファイルを保存
    with open(temp_filepath, "wb") as f:
        f.write(file_data)

    return file_id

def get_temp_file_path(file_id: str, session_id: str, user_id: str) -> Optional[str]:
    """
    ファイルIDからファイルパスを取得

    Args:
        file_id: ファイルID
        session_id: セッションID
        user_id: ユーザーID

    Returns:
        ファイルパス（存在しない場合はNone）
    """
    # 一時ディレクトリが存在しない場合はNoneを返す
    if not os.path.exists(TEMP_UPLOAD_DIR):
        return None

    # ユーザーID、セッションID、ファイルIDでファイルを検索
    try:
        for filename in os.listdir(TEMP_UPLOAD_DIR):
            if filename.startswith(f"{user_id}_{session_id}_{file_id}"):
                return os.path.join(TEMP_UPLOAD_DIR, filename)
    except OSError:
        # ディレクトリの読み取りに失敗した場合
        return None
    return None

def cleanup_temp_files(session_id: str, user_id: str, max_age_hours: int = 24):
    """
    古い一時ファイルをクリーンアップ

    Args:
        session_id: セッションID（必須）
        user_id: ユーザーID（必須）
        max_age_hours: ファイルの最大保持時間（時間）
    """
    if not os.path.exists(TEMP_UPLOAD_DIR):
        return

    # user_idとsession_idが両方とも有効でない場合は、安全のため何もしない
    if not user_id or not session_id:
        return

    current_time = datetime.datetime.now()

    for filename in os.listdir(TEMP_UPLOAD_DIR):
        filepath = os.path.join(TEMP_UPLOAD_DIR, filename)

        # 指定されたユーザーとセッションのファイルのみを対象とする
        if not filename.startswith(f"{user_id}_{session_id}_"):
            continue

        # ファイルの作成時間をチェック
        file_time = datetime.datetime.fromtimestamp(os.path.getctime(filepath))
        if (current_time - file_time).total_seconds() > max_age_hours * 3600:
            try:
                os.remove(filepath)
            except OSError:
                pass  # ファイル削除に失敗しても続行

def delete_temp_file(file_id: str, session_id: str, user_id: str) -> bool:
    """
    指定された一時ファイルを削除

    Args:
        file_id: ファイルID
        session_id: セッションID
        user_id: ユーザーID

    Returns:
        削除に成功した場合True、失敗した場合False
    """
    if not os.path.exists(TEMP_UPLOAD_DIR):
        print(f"⚠️ 一時ディレクトリ:{TEMP_UPLOAD_DIR}が存在しません。削除できません。")
        return False

    # user_idとsession_idが両方とも有効でない場合は、安全のため何もしない
    if not user_id or not session_id or not file_id:
        print(f"⚠️ 無効なパラメータ: user_id:{user_id}, session_id:{session_id}, または file_id:{file_id} が指定されていません。削除できません。")
        return False

    # ファイルパスを取得
    temp_file_path = get_temp_file_path(file_id, session_id, user_id)
    if not temp_file_path or not os.path.exists(temp_file_path):
        print(f"⚠️ ファイルパス {temp_file_path} に対応するファイルが見つかりません。削除できません。")
        return False

    try:
        os.remove(temp_file_path)
        return True
    except OSError as e:
        print(f"⚠️ ファイル {temp_file_path} の削除に失敗しました。{str(e)}")
        return False

class ConversationHistoryResponse(BaseModel):
    id: int
    session_id: str
    user_id: Optional[str]
    agent_type: str
    agent_manager_id: Optional[str]
    user_message: str
    agent_response: str
    message_type: str
    llm_type: Optional[str]
    is_collaboration: bool
    created_at: str
    html_content: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    evaluation_status: Optional[Dict[str, Any]] = None  # 評価状態

class ConversationContextRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    agent_manager_id: Optional[str] = None
    include_html: bool = False
    limit: int = 20

class EvaluationRequest(BaseModel):
    trace_id: str
    evaluation: str  # "good" または "bad"
    user_id: Optional[str] = None
    comment: Optional[str] = None

class RegenerateRequest(BaseModel):
    query: str
    context: Optional[str] = None
    session_id: Optional[str] = None
    agent_type: Optional[str] = None
    conversation_id: Optional[int] = None  # 再生成する位置を特定するためのconversation ID

# 在文件顶部添加配置 - 環境変数から動的に取得
AGENT_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

@router.post("/evaluate_response")
async def evaluate_response(
    trace_id: str = Form(...),
    evaluation: str = Form(...),  # "good" または "bad"
    user_id: Optional[str] = Form(None),
    comment: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """ユーザーのAgent応答に対する評価を処理"""
    try:
        # Langfuseが利用可能かチェック
        if not langfuse_handler.is_available():
            # Langfuse無効でも評価状態を保存
            _save_evaluation_status(db, trace_id, evaluation, user_id, comment)
            return {
                "status": "success", 
                "message": "評価を受信しました（Langfuse無効）",
                "evaluation": evaluation,
                "score": 1 if evaluation == "good" else 0
            }

        # Langfuse評価を作成
        score_value = 1 if evaluation == "good" else 0
        evaluation_comment = comment or f"ユーザーフィードバック: {evaluation}"

        # langfuse_handlerのクライアントを使用（Langfuse V3対応）
        langfuse_handler.langfuse_client.create_score(
            trace_id=trace_id,
            name="user_feedback",
            value=score_value,
            comment=evaluation_comment,
        )

        # 評価状態をデータベースに保存
        _save_evaluation_status(db, trace_id, evaluation, user_id, comment)

        return {
            "status": "success", 
            "message": "評価が正常に送信されました",
            "evaluation": evaluation,
            "score": score_value
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"評価の送信に失敗しました: {str(e)}"
        )

@router.post("/regenerate_response")
async def regenerate_response(
    query: str = Form(...),
    context: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    agent_type: Optional[str] = Form("default"),
    conversation_id: Optional[int] = Form(None),
    llm_type: Optional[str] = Form("ollama"),
    db: Session = Depends(get_db)
):
    """エージェント応答を再生成"""

    # 1. エージェントタイプに基づいて適切なAPIを呼び出す
    new_response = None
    agent_response_data = None

    try:
        async with httpx.AsyncClient() as client:
            # 前端と同じAPIエンドポイント決定ロジック
            if agent_type == "AgentDirector":
                api_url = f"{AGENT_API_BASE_URL}/api/agent/director-agent/chat"
            else:
                # 他のエージェントの場合は単一エージェントAPIを使用
                api_url = f"{AGENT_API_BASE_URL}/api/agent/single-agent/chat"

            # 前端と同じリクエストボディ構造
            payload = {
                "message": query,
                "user_id": user_id or "",
                "session_id": session_id or "",
                "llm_type": llm_type,
                "agent_type": agent_type,
                "context": context if context else {}
            }

            # HTTPリクエストを送信
            response = await client.post(
                api_url,
                json=payload,
                timeout=300  # タイムアウト時間を設定
            )

            # レスポンスステータスを確認
            if response.status_code == 200:
                agent_response_data = response.json()

                # レスポンスからテキストを抽出
                if isinstance(agent_response_data, dict):
                    new_response = agent_response_data.get('response', str(agent_response_data))
                else:
                    new_response = str(agent_response_data)
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Agent API呼び出しが失敗しました: {response.text}"
                )
    except httpx.TimeoutException:
        print("⚠️ Agent API呼び出しタイムアウト")
        new_response = "申し訳ございません。応答の生成に時間がかかりすぎました。もう一度お試しください。"
        raise HTTPException(status_code=408, detail=new_response)
    except httpx.RequestError as e:
        print(f"⚠️ Agent APIリクエストエラー: {e}")
        new_response = f"申し訳ございません。Agent APIへの接続に失敗しました: {str(e)}"
        raise HTTPException(status_code=503, detail=new_response)
    except Exception as agent_error:
        print(f"⚠️ エージェント応答生成エラー: {agent_error}")
        new_response = f"申し訳ございません。応答の再生成中にエラーが発生しました: {str(agent_error)}"
        raise HTTPException(status_code=500, detail=new_response)

    # 2. 指定されたconversation_idより後の古い履歴を削除
    deleted_count = 0
    if session_id and conversation_id:
        try:
            deleted_count = ConversationService.delete_conversations_by_id(
                db, session_id, conversation_id
            )
            print(f"✅ 古い履歴を削除しました: {deleted_count}件")
        except Exception as delete_error:
            print(f"⚠️ 古い履歴削除エラー: {delete_error}")

    # 3. 前端が期待するJSON形式でレスポンスを返す
    response_data = {
        "response": new_response,
        "html_content": None,
        "trace_id": None,
        "conversation_id": None,
        "deleted_conversations": deleted_count,
        "status": "success",
        "message": "応答が正常に再生成されました"
    }

    # agent_response_dataから追加情報を抽出
    if isinstance(agent_response_data, dict):
        response_data.update({
            "html_content": agent_response_data.get("html_content"),
            "trace_id": agent_response_data.get("trace_id"),
            "conversation_id": agent_response_data.get("conversation_id"),
            "action_type": agent_response_data.get("action_type"),
            "workflow_step": agent_response_data.get("workflow_step"),
            "llm_type_used": agent_response_data.get("llm_type_used"),
            "agent_type": agent_response_data.get("agent_type"),
            "next_actions": agent_response_data.get("next_actions"),
            "session_id": agent_response_data.get("session_id"),
            "user_id": agent_response_data.get("user_id"),
            "error_message": agent_response_data.get("error_message")
        })

    return response_data


@router.get("/history/{session_id}")
async def get_session_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """セッション会話履歴を取得"""
    try:
        conversations = ConversationService.get_session_history(db, session_id, limit)

        return {
            "session_id": session_id,
            "count": len(conversations),
            "conversations": [
                ConversationHistoryResponse(
                    id=conv.id,
                    session_id=conv.session_id,
                    user_id=conv.user_id,
                    agent_type=conv.agent_type,
                    agent_manager_id=conv.agent_manager_id,
                    user_message=conv.user_message,
                    agent_response=conv.agent_response,
                    message_type=conv.message_type,
                    llm_type=conv.llm_type,
                    is_collaboration=conv.is_collaboration,
                    created_at=conv.created_at.isoformat(),
                    html_content=conv.html_content,
                    context_data=conv.context_data,
                    trace_id=conv.context_data.get("trace_id") if conv.context_data else None,
                    evaluation_status=conv.context_data.get("evaluation") if conv.context_data else None
                ) for conv in conversations
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"履歴取得に失敗しました: {str(e)}")

@router.get("/history/users/all")
async def get_all_users_history(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """全ユーザーのチャット履歴をユーザーIDとセッションIDでグループ化して取得"""
    try:
        # 全ての会話履歴を取得（最新順）
        conversations = db.query(ConversationHistory)\
            .order_by(ConversationHistory.created_at.desc())\
            .limit(limit * 3)\
            .all()  # より多くのレコードを取得してからグループ化

        # ユーザーIDとセッションIDでグループ化
        user_sessions = {}

        for conv in conversations:
            user_id = conv.user_id or 'anonymous'
            session_id = conv.session_id

            if user_id not in user_sessions:
                user_sessions[user_id] = {}

            if session_id not in user_sessions[user_id]:
                user_sessions[user_id][session_id] = {
                    'session_id': session_id,
                    'message_count': 0,
                    'first_message': None,
                    'latest_message': None,
                    'last_activity': None
                }

            session_data = user_sessions[user_id][session_id]
            session_data['message_count'] += 1

            # 最初のメッセージを保存
            if session_data['first_message'] is None:
                session_data['first_message'] = conv.user_message

            # 最新のメッセージと時刻を更新（時系列順で最初に来るのが最新）
            if session_data['last_activity'] is None or conv.created_at > session_data['last_activity']:
                session_data['latest_message'] = conv.user_message
                session_data['last_activity'] = conv.created_at

        # レスポンス形式に変換
        result = []
        for user_id, sessions in user_sessions.items():
            sessions_list = list(sessions.values())
            # セッションを最新のアクティビティ順でソート
            sessions_list.sort(key=lambda x: x['last_activity'], reverse=True)

            result.append({
                'user_id': user_id,
                'sessions': sessions_list[:20]  # ユーザーあたり最大20セッション
            })

        # ユーザーを最新のアクティビティ順でソート
        result.sort(key=lambda x: max(s['last_activity'] for s in x['sessions']) if x['sessions'] else '', reverse=True)

        return {
            "user_sessions": result[:10]  # 最大10ユーザー
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"履歴取得に失敗しました: {str(e)}")

@router.post("/context")
async def get_conversation_context(
    request: ConversationContextRequest,
    db: Session = Depends(get_db)
):
    """会話コンテキストを取得（異なるエージェント間での共有履歴を含む）"""
    try:
        # セッション履歴を取得
        session_history = ConversationService.get_session_history(
            db, request.session_id, request.limit // 2
        )

        # 異なるエージェント間での履歴を取得
        cross_agent_history = ConversationService.get_cross_agent_history(
            db,
            session_id=request.session_id,
            user_id=request.user_id,
            agent_manager_id=request.agent_manager_id,
            limit=request.limit // 2
        )

        # 履歴をマージ
        all_history = list({conv.id: conv for conv in (session_history + cross_agent_history)}.values())
        all_history.sort(key=lambda x: x.created_at, reverse=True)

        # フォーマット
        formatted_context = ConversationService.format_history_for_context(
            all_history[:request.limit],
            include_html=request.include_html
        )

        return {
            "session_id": request.session_id,
            "context_count": len(formatted_context),
            "context": formatted_context,
            "has_cross_agent_data": len(cross_agent_history) > 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"コンテキスト取得に失敗しました: {str(e)}")

@router.get("/agents/{agent_type}/recent")
async def get_agent_recent_conversations(
    agent_type: str,
    hours: int = Query(24, ge=1, le=168),  # 1-168時間（1週間）
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """特定エージェントの最近の会話を取得"""
    try:
        conversations = ConversationService.get_agent_conversations(
            db, agent_type, hours, limit
        )

        return {
            "agent_type": agent_type,
            "time_range_hours": hours,
            "count": len(conversations),
            "conversations": ConversationService.format_history_for_context(conversations)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エージェント履歴取得に失敗しました: {str(e)}")

@router.delete("/cleanup")
async def cleanup_old_conversations(
    days: int = Query(30, ge=7, le=365),  # 7日-1年
    db: Session = Depends(get_db)
):
    """古い会話履歴をクリーンアップ"""
    try:
        deleted_count = ConversationService.clean_old_conversations(db, days)

        return {
            "message": f"{days}日より古い会話履歴をクリーンアップしました",
            "deleted_count": deleted_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"クリーンアップに失敗しました: {str(e)}")

@router.delete("/history/{session_id}")
async def clear_session_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """セッション会話履歴をクリア"""
    try:
        deleted_count = ConversationService.clear_session_history(db, session_id)

        return {
            "message": f"セッション {session_id} の会話履歴をクリアしました",
            "deleted_count": deleted_count,
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"履歴クリアに失敗しました: {str(e)}")

@router.post("/voice_input")
async def process_voice_input(
    audio_file: UploadFile = File(...),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    agent_type: Optional[str] = Form("default"),
    llm_type: Optional[str] = Form("ollama"),
    context: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    音声入力を処理してテキストに変換し、既存のチャットワークフローに送信

    Args:
        audio_file: アップロードされた音声ファイル
        session_id: セッションID
        user_id: ユーザーID
        agent_type: エージェントタイプ
        llm_type: LLMタイプ
        context: コンテキスト情報
        db: データベースセッション

    Returns:
        音声変換結果とチャット応答
    """
    voice_service = VoiceService()

    # 音声サービスが利用可能かチェック
    if not voice_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="音声機能が利用できません。OpenAI APIキーが設定されていることを確認してください。"
        )

    # サポートされているファイル形式をチェック
    if audio_file.filename:
        file_extension = audio_file.filename.split('.')[-1].lower()
        if file_extension not in voice_service.get_supported_formats():
            raise HTTPException(
                status_code=400,
                detail=f"サポートされていないファイル形式です。サポート形式: {', '.join(voice_service.get_supported_formats())}"
            )

    try:
        # 音声ファイルを読み込み
        audio_data = await audio_file.read()

        # 音声をテキストに変換（Langfuse追跡付き）
        transcribed_text = await voice_service.transcribe_audio(
            audio_data, 
            audio_file.filename or "audio.wav",
            session_id=session_id,
            user_id=user_id
        )

        if not transcribed_text or not transcribed_text.strip():
            raise HTTPException(
                status_code=400,
                detail="音声からテキストを抽出できませんでした。音声が明確に録音されているか確認してください。"
            )

        # 変換されたテキストを既存のチャットワークフローに送信
        # regenerate_response関数と同じロジックを使用
        agent_response_data = None

        try:
            async with httpx.AsyncClient() as client:
                # エージェントAPIエンドポイントを決定
                if agent_type == "AgentDirector":
                    api_url = f"{AGENT_API_BASE_URL}/api/agent/director-agent/chat"
                else:
                    api_url = f"{AGENT_API_BASE_URL}/api/agent/single-agent/chat"

                # リクエストペイロードを構築
                payload = {
                    "message": transcribed_text,
                    "user_id": user_id or "",
                    "session_id": session_id or "",
                    "llm_type": llm_type,
                    "agent_type": agent_type,
                    "context": context if context else {}
                }

                # エージェントAPIを呼び出し
                response = await client.post(api_url, json=payload, timeout=120.0)

                if response.status_code == 200:
                    agent_response_data = response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"エージェントAPI呼び出しに失敗しました: {response.text}"
                    )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="エージェント応答がタイムアウトしました。しばらく待ってから再試行してください。"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"エージェントサービスに接続できません: {str(e)}"
            )

        return {
            "status": "success",
            "transcribed_text": transcribed_text,
            "agent_response": agent_response_data,
            "message": "音声入力が正常に処理されました"
        }

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"音声処理中にエラーが発生しました: {str(e)}"
        )

@router.post("/temp_file_upload")
async def upload_temp_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user_id: Optional[str] = Form(None)
):
    """
    ファイルを一時ディレクトリにアップロードし、後で処理するためのファイルIDを返す

    Args:
        file: アップロードするファイル
        session_id: セッションID
        user_id: ユーザーID

    Returns:
        ファイルID、ファイル名、ファイルサイズなどの情報
    """
    # ファイルサイズをチェック（10MB制限）
    max_size = 10 * 1024 * 1024  # 10MB
    file_data = await file.read()

    if len(file_data) > max_size:
        raise HTTPException(
            status_code=400,
            detail="ファイルサイズが大きすぎます。10MB以下のファイルを選択してください。"
        )

    # サポートされているファイル形式をチェック（画像のみ）
    image_service = ImageService()
    if file.filename:
        file_extension = file.filename.split('.')[-1].lower()
        if file_extension not in image_service.get_supported_formats():
            raise HTTPException(
                status_code=400,
                detail=f"サポートされていないファイル形式です。サポート形式: {', '.join(image_service.get_supported_formats())}"
            )

    try:
        # user_idがNoneの場合はデフォルト値を使用
        effective_user_id = user_id or "default_user"

        # 一時ファイルとして保存
        file_id = save_temp_file(file_data, file.filename or "uploaded_file", session_id, effective_user_id)

        # 古いファイルをクリーンアップ
        cleanup_temp_files(session_id, effective_user_id)

        return {
            "status": "success",
            "file_id": file_id,
            "filename": file.filename,
            "file_size": len(file_data),
            "session_id": session_id,
            "message": "ファイルが一時保存されました。テキストまたは音声で指示を入力してください。"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ファイルの一時保存に失敗しました: {str(e)}"
        )

@router.delete("/temp_file_delete")
async def delete_temp_file_endpoint(
    file_id: str = Form(...),
    session_id: str = Form(...),
    user_id: Optional[str] = Form(None)
):
    """
    指定された一時ファイルを削除

    Args:
        file_id: 削除するファイルのID
        session_id: セッションID
        user_id: ユーザーID

    Returns:
        削除結果
    """
    try:
        # user_idがNoneの場合はデフォルト値を使用
        effective_user_id = user_id or "default_user"

        # ファイルを削除
        success = delete_temp_file(file_id, session_id, effective_user_id)

        if success:
            return {
                "status": "success",
                "file_id": file_id,
                "message": "ファイルが正常に削除されました"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="指定されたファイルが見つからないか、削除に失敗しました"
            )

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ファイル削除中にエラーが発生しました: {str(e)}"
        )

@router.post("/process_message_with_files")
async def process_message_with_files(
    message: str = Form(...),
    file_ids: Optional[str] = Form(None),  # カンマ区切りのファイルIDリスト
    session_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    agent_type: Optional[str] = Form("default"),
    llm_type: Optional[str] = Form("ollama"),
    context: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    ユーザーメッセージと一時保存されたファイルを一緒に処理

    Args:
        message: ユーザーメッセージ
        file_ids: 一時保存されたファイルのIDリスト（カンマ区切り）
        session_id: セッションID
        user_id: ユーザーID
        agent_type: エージェントタイプ
        llm_type: LLMタイプ
        context: コンテキスト情報
        db: データベースセッション

    Returns:
        処理結果とエージェント応答
    """
    try:
        final_message = message
        processed_files = []

        # ファイルIDが指定されている場合、ファイルを処理
        if file_ids and file_ids.strip():
            image_service = ImageService()

            # 画像サービスが利用可能かチェック
            if not image_service.is_available():
                raise HTTPException(
                    status_code=503,
                    detail="画像分析機能が利用できません。OpenAI APIキーが設定されていることを確認してください。"
                )

            file_id_list = [fid.strip() for fid in file_ids.split(",") if fid.strip()]

            for file_id in file_id_list:
                # user_idがNoneの場合はデフォルト値を使用
                effective_user_id = user_id or "default_user"

                # 一時ファイルのパスを取得
                temp_file_path = get_temp_file_path(file_id, session_id, effective_user_id)
                if not temp_file_path or not os.path.exists(temp_file_path):
                    raise HTTPException(
                        status_code=404,
                        detail=f"ファイルID {file_id} に対応するファイルが見つかりません。"
                    )

                # ファイルを読み込み
                with open(temp_file_path, "rb") as f:
                    file_data = f.read()

                # ファイル名を取得
                filename = os.path.basename(temp_file_path)

                # 画像を分析
                image_analysis = await image_service.analyze_image(
                    file_data,
                    filename,
                    user_prompt=message,
                    session_id=session_id,
                    user_id=user_id
                )

                if image_analysis and image_analysis.strip():
                    processed_files.append({
                        "file_id": file_id,
                        "filename": filename,
                        "analysis": image_analysis
                    })

            # 画像分析結果をメッセージに統合
            if processed_files:
                file_analyses = []
                for pf in processed_files:
                    file_analyses.append(f"【ファイル: {pf['filename']}】\n{pf['analysis']}")

                files_section = "\n\n".join(file_analyses)
                final_message = f"[Instruction from User]\n{message}\n\n[Analysis Result of the Uploaded File]\n{files_section}\n\nBased on the above file analysis result, please respond according to the user’s instructions."

        # エージェントAPIに送信
        agent_response_data = None

        try:
            async with httpx.AsyncClient() as client:
                # エージェントAPIエンドポイントを決定
                if agent_type == "AgentDirector":
                    api_url = f"{AGENT_API_BASE_URL}/api/agent/director-agent/chat"
                else:
                    api_url = f"{AGENT_API_BASE_URL}/api/agent/single-agent/chat"

                # リクエストペイロードを構築
                payload = {
                    "message": final_message,
                    "user_id": user_id or "",
                    "session_id": session_id,
                    "llm_type": llm_type,
                    "agent_type": agent_type,
                    "context": context if context else {}
                }

                # エージェントAPIを呼び出し
                response = await client.post(api_url, json=payload, timeout=120.0)

                if response.status_code == 200:
                    agent_response_data = response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"エージェントAPI呼び出しに失敗しました: {response.text}"
                    )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="エージェント応答がタイムアウトしました。しばらく待ってから再試行してください。"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"エージェントサービスに接続できません: {str(e)}"
            )

        # 処理完了後、使用したファイルを削除
        if file_ids and file_ids.strip():
            # user_idがNoneの場合はデフォルト値を使用
            effective_user_id = user_id or "default_user"

            file_id_list = [fid.strip() for fid in file_ids.split(",") if fid.strip()]
            for file_id in file_id_list:
                temp_file_path = get_temp_file_path(file_id, session_id, effective_user_id)
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                    except OSError:
                        pass  # ファイル削除に失敗しても続行

        return {
            "status": "success",
            "original_message": message,
            "final_message": final_message,
            "processed_files": processed_files,
            "agent_response": agent_response_data,
            "message": "メッセージとファイルが正常に処理されました"
        }

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"メッセージ処理中にエラーが発生しました: {str(e)}"
        )

@router.post("/image_input")
async def process_image_input(
    image_file: UploadFile = File(...),
    user_message: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    agent_type: Optional[str] = Form("default"),
    llm_type: Optional[str] = Form("ollama"),
    context: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    画像入力を処理して分析し、既存のチャットワークフローに送信

    Args:
        image_file: アップロードされた画像ファイル
        user_message: ユーザーからのテキストメッセージ（オプション）
        session_id: セッションID
        user_id: ユーザーID
        agent_type: エージェントタイプ
        llm_type: LLMタイプ
        context: コンテキスト情報
        db: データベースセッション

    Returns:
        画像分析結果とチャット応答
    """
    image_service = ImageService()

    # 画像サービスが利用可能かチェック
    if not image_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="画像分析機能が利用できません。OpenAI APIキーが設定されていることを確認してください。"
        )

    # サポートされているファイル形式をチェック
    if image_file.filename:
        file_extension = image_file.filename.split('.')[-1].lower()
        if file_extension not in image_service.get_supported_formats():
            raise HTTPException(
                status_code=400,
                detail=f"サポートされていないファイル形式です。サポート形式: {', '.join(image_service.get_supported_formats())}"
            )

    try:
        # 画像ファイルを読み込み
        image_data = await image_file.read()

        # 画像を分析（Langfuse追跡付き）
        image_analysis = await image_service.analyze_image(
            image_data, 
            image_file.filename or "image.jpg",
            user_prompt=user_message,
            session_id=session_id,
            user_id=user_id
        )

        if not image_analysis or not image_analysis.strip():
            raise HTTPException(
                status_code=400,
                detail="画像から情報を抽出できませんでした。画像が明確で読み取り可能か確認してください。"
            )

        # 画像分析結果とユーザーメッセージをマージ
        merged_message = image_service.merge_image_analysis_with_text(image_analysis, user_message)

        # マージされたメッセージを既存のチャットワークフローに送信
        agent_response_data = None

        try:
            async with httpx.AsyncClient() as client:
                # エージェントAPIエンドポイントを決定
                if agent_type == "AgentDirector":
                    api_url = f"{AGENT_API_BASE_URL}/api/agent/director-agent/chat"
                else:
                    api_url = f"{AGENT_API_BASE_URL}/api/agent/single-agent/chat"

                # リクエストペイロードを構築
                payload = {
                    "message": merged_message,
                    "user_id": user_id or "",
                    "session_id": session_id or "",
                    "llm_type": llm_type,
                    "agent_type": agent_type,
                    "context": context if context else {}
                }

                # エージェントAPIを呼び出し
                response = await client.post(api_url, json=payload, timeout=120.0)

                if response.status_code == 200:
                    agent_response_data = response.json()
                else:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"エージェントAPI呼び出しに失敗しました: {response.text}"
                    )

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail="エージェント応答がタイムアウトしました。しばらく待ってから再試行してください。"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503,
                detail=f"エージェントサービスに接続できません: {str(e)}"
            )

        return {
            "status": "success",
            "image_analysis": image_analysis,
            "user_message": user_message,
            "merged_message": merged_message,
            "agent_response": agent_response_data,
            "message": "画像入力が正常に処理されました"
        }

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"画像処理中にエラーが発生しました: {str(e)}"
        )

def _save_evaluation_status(db: Session, trace_id: str, evaluation: str, user_id: Optional[str] = None, comment: Optional[str] = None):
    """評価状態をデータベースに保存"""
    try:
        # trace_idで該当する会話履歴を検索
        conversation = db.query(ConversationHistory).filter(
            ConversationHistory.context_data.contains({"trace_id": trace_id})
        ).first()

        if conversation:
            # 既存のcontext_dataを取得（なければ空の辞書）
            context_data = conversation.context_data or {}

            # 評価情報を追加
            context_data["evaluation"] = {
                "status": evaluation,  # "good" または "bad"
                "user_id": user_id,
                "comment": comment,
                "evaluated_at": datetime.datetime.now(datetime.UTC).isoformat()
            }

            # context_dataを更新
            conversation.context_data = context_data
            # SQLAlchemyのflag_modifiedを使用して変更を通知
            flag_modified(conversation, "context_data")
            conversation.updated_at = datetime.datetime.now(datetime.UTC)

            db.commit()
            print(f"✅ 評価状態を保存しました: trace_id={trace_id}, evaluation={evaluation}")
        else:
            print(f"⚠️ trace_id={trace_id}に対応する会話履歴が見つかりませんでした")

    except Exception as e:
        print(f"❌ 評価状態の保存に失敗しました: {str(e)}")
        db.rollback()
