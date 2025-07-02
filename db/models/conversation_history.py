from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, JSON
import datetime
from db.database import Base


class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)  # 自增主键
    session_id = Column(String(255), index=True)  # 会话ID（索引）
    user_id = Column(String(255), nullable=True, index=True)  # 用户ID（索引）
    agent_type = Column(String(100), nullable=False, index=True)  # エージェントタイプ
    agent_manager_id = Column(String(255), nullable=True, index=True)  # Agent Manager ID
    
    # メッセージ内容
    user_message = Column(Text, nullable=False)  # ユーザーメッセージ
    agent_response = Column(Text, nullable=False)  # エージェントレスポンス
    
    # メタデータ
    message_type = Column(String(50), default='chat')  # メッセージタイプ（chat, command, error等）
    llm_type = Column(String(100), nullable=True)  # 使用されたLLMタイプ
    
    # 処理情報
    context_data = Column(JSON, nullable=True)  # コンテキストデータ（JSON形式）
    html_content = Column(Text, nullable=True)  # 生成されたHTML内容
    error_info = Column(Text, nullable=True)  # エラー情報
    next_actions = Column(Text, nullable=True)  # 次のアクション提案
    
    # 協作情報
    is_collaboration = Column(Boolean, default=False)  # 協作モードフラグ
    collaboration_agents = Column(JSON, nullable=True)  # 協作に参加したエージェント情報
    routing_decision = Column(JSON, nullable=True)  # ルーティング決定情報
    
    # タイムスタンプ
    created_at = Column(DateTime, default=datetime.datetime.now, index=True)  # 作成時間（ローカル時間）
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)  # 更新時間（ローカル時間）