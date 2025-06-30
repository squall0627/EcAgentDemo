from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from db.database import get_db
from services.conversation_service import ConversationService
from db.models.conversation_history import ConversationHistory

router = APIRouter()

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

class ConversationContextRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    agent_manager_id: Optional[str] = None
    include_html: bool = False
    limit: int = 20

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
                    context_data=conv.context_data
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