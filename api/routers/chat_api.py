import httpx
from fastapi import APIRouter, HTTPException, Depends, Query, Form
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm.attributes import flag_modified
from db.database import get_db
from services.conversation_service import ConversationService
from db.models.conversation_history import ConversationHistory
from utils.langfuse_handler import get_global_langfuse_handler
import datetime

router = APIRouter()

# Langfuseハンドラーを取得（既存の初期化済みクライアントを使用）
langfuse_handler = get_global_langfuse_handler()

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

# 在文件顶部添加配置
AGENT_API_BASE_URL = "http://localhost:5004"  # TODO 根据您的实际配置调整

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
    """Agent応答を再生成"""

    # 1. 根据agent_type调用相应的API
    new_response = None
    agent_response_data = None

    try:
        async with httpx.AsyncClient() as client:
            # if agent_type in ["multi", "collaboration"]:
            #     # 调用多agent API
            #     api_url = f"{AGENT_API_BASE_URL}/api/agent/multi-agent/chat"
            #     payload = {
            #         "message": query,
            #         "context": context or "",
            #         "llm_type": llm_type,
            #         "session_id": session_id or "",
            #         "user_id": user_id or "",
            #         "agent_type": None if agent_type == "multi" else agent_type,
            #         "enable_collaboration": agent_type == "collaboration"  # TODO
            #     }
            #
            #     # 如果是协作模式，添加协作参数
            #     if agent_type == "collaboration":
            #         payload["collaboration"] = True
            #
            # else:
            #     # 调用单agent API
            #     api_url = f"{AGENT_API_BASE_URL}/api/agent/single-agent/chat"
            #     payload = {
            #         "message": query,
            #         "llm_type": llm_type,
            #         "session_id": session_id or "",
            #         "user_id": user_id or ""
            #     }
            #
            #     # 如果有context，添加到payload中
            #     if context:
            #         payload["context"] = context

            api_url = f"{AGENT_API_BASE_URL}/api/agent/director-agent/chat"
            payload = {
                "message": query,
                "llm_type": llm_type,
                "session_id": session_id or "",
                "user_id": user_id or "",
                "is_entry_agent": True,
            }

            # 如果有context，添加到payload中
            if context:
                payload["context"] = context


            # 发送HTTP请求
            response = await client.post(
                api_url,
                json=payload,
                timeout=300  # TODO 设置超时时间
            )

            # 检查响应状态
            if response.status_code == 200:
                agent_response_data = response.json()

                # 从响应中提取文本
                if isinstance(agent_response_data, dict):
                    new_response = agent_response_data.get('response', str(agent_response_data))
                else:
                    new_response = str(agent_response_data)
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Agent API调用失败: {response.text}"
                )
    except httpx.TimeoutException:
        print("⚠️ Agent API调用超时")
        new_response = "申し訳ございません。応答の生成に時間がかかりすぎました。もう一度お試しください。"
        raise HTTPException(status_code=500, detail=new_response)
    except httpx.RequestError as e:
        print(f"⚠️ Agent API请求错误: {e}")
        new_response = f"申し訳ございません。Agent APIへの接続に失敗しました: {str(e)}"
        raise HTTPException(status_code=500, detail=new_response)
    except Exception as agent_error:
        print(f"⚠️ Agent応答生成エラー: {agent_error}")
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

    # 3. フロントエンドが期待するJSON形式でレスポンスを返す
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
            "next_actions": agent_response_data.get("next_actions")
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
