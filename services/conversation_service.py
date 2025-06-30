from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta
from db.models.conversation_history import ConversationHistory
from db.database import get_db
import json


class ConversationService:
    """会話履歴管理サービス"""
    
    @staticmethod
    def save_conversation(
        db: Session,
        session_id: str,
        user_id: Optional[str],
        agent_type: str,
        agent_manager_id: Optional[str],
        user_message: str,
        agent_response: str,
        message_type: str = 'chat',
        llm_type: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        html_content: Optional[str] = None,
        error_info: Optional[str] = None,
        next_actions: Optional[str] = None,
        is_collaboration: bool = False,
        collaboration_agents: Optional[List[Dict[str, Any]]] = None,
        routing_decision: Optional[Dict[str, Any]] = None
    ) -> ConversationHistory:
        """会話履歴を保存"""
        
        conversation = ConversationHistory(
            session_id=session_id,
            user_id=user_id,
            agent_type=agent_type,
            agent_manager_id=agent_manager_id,
            user_message=user_message,
            agent_response=agent_response,
            message_type=message_type,
            llm_type=llm_type,
            context_data=context_data,
            html_content=html_content,
            error_info=error_info,
            next_actions=next_actions,
            is_collaboration=is_collaboration,
            collaboration_agents=collaboration_agents,
            routing_decision=routing_decision
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation
    
    @staticmethod
    def get_session_history(
        db: Session,
        session_id: str,
        limit: int = 50
    ) -> List[ConversationHistory]:
        """セッション履歴を取得"""
        return db.query(ConversationHistory)\
            .filter(ConversationHistory.session_id == session_id)\
            .order_by(desc(ConversationHistory.created_at))\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_cross_agent_history(
        db: Session,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_manager_id: Optional[str] = None,
        limit: int = 50
    ) -> List[ConversationHistory]:
        """異なるエージェント間での履歴を取得"""
        query = db.query(ConversationHistory)
        
        filters = []
        if session_id:
            filters.append(ConversationHistory.session_id == session_id)
        if user_id:
            filters.append(ConversationHistory.user_id == user_id)
        if agent_manager_id:
            filters.append(ConversationHistory.agent_manager_id == agent_manager_id)
        
        if filters:
            query = query.filter(and_(*filters))
        
        return query.order_by(desc(ConversationHistory.created_at))\
            .limit(limit)\
            .all()
    
    @staticmethod
    def get_agent_conversations(
        db: Session,
        agent_type: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[ConversationHistory]:
        """特定エージェントの最近の会話を取得"""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        return db.query(ConversationHistory)\
            .filter(and_(
                ConversationHistory.agent_type == agent_type,
                ConversationHistory.created_at >= since
            ))\
            .order_by(desc(ConversationHistory.created_at))\
            .limit(limit)\
            .all()
    
    @staticmethod
    def format_history_for_context(
        conversations: List[ConversationHistory],
        include_html: bool = False
    ) -> List[Dict[str, Any]]:
        """履歴をコンテキスト用フォーマットに変換"""
        formatted = []
        
        for conv in conversations:
            entry = {
                "timestamp": conv.created_at.isoformat(),
                "agent_type": conv.agent_type,
                "user_message": conv.user_message,
                "agent_response": conv.agent_response,
                "message_type": conv.message_type,
                "llm_type": conv.llm_type
            }
            
            if include_html and conv.html_content:
                entry["html_content"] = conv.html_content
            
            if conv.context_data:
                entry["context_data"] = conv.context_data
            
            if conv.is_collaboration:
                entry["collaboration_info"] = {
                    "is_collaboration": True,
                    "agents": conv.collaboration_agents,
                    "routing": conv.routing_decision
                }
            
            formatted.append(entry)
        
        return formatted
    
    @staticmethod
    def clean_old_conversations(
        db: Session,
        days: int = 30
    ) -> int:
        """古い会話履歴をクリーンアップ"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        deleted_count = db.query(ConversationHistory)\
            .filter(ConversationHistory.created_at < cutoff_date)\
            .delete()
        
        db.commit()
        return deleted_count

    @staticmethod
    def clear_session_history(db: Session, session_id: str) -> int:
        """指定されたセッションの会話履歴をクリア"""
        try:
            deleted_count = db.query(ConversationHistory)\
                .filter(ConversationHistory.session_id == session_id)\
                .delete()
            db.commit()
            return deleted_count
        except Exception as e:
            db.rollback()
            raise e