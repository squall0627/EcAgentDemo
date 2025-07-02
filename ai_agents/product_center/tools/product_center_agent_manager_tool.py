import json
from typing import Optional, Type
from pydantic import BaseModel, Field

from langchain.tools import BaseTool

from ai_agents.product_center.product_center_agent_manager import ProductCenterAgentManager


class ManagerToolInput(BaseModel):
    """Manager Tool用の入力スキーマ"""
    command: str = Field(description="実行するコマンド")
    llm_type: Optional[str] = Field(default=None, description="使用するLLMのタイプ")
    session_id: Optional[str] = Field(default=None, description="セッションID")
    user_id: Optional[str] = Field(default=None, description="ユーザーID")
    is_entry_agent: Optional[bool] = Field(default=False, description="エージェントとしてのエントリーかどうか")


class ProductCenterAgentManagerTool(BaseTool):
    """
    ProductCenterAgentManagerをTool化したクラス
    AgentDirectorから呼び出される商品センター管理専門ツール
    """
    name: str = "product_center_agent_manager"
    description: str = "商品センター管理専門Manager - 商品検索、在庫管理、価格設定、棚上げ・棚下げ等の商品関連業務を処理"
    args_schema: Type[BaseModel] = ManagerToolInput

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """ProductCenterAgentManagerTool初期化"""
        super().__init__()
        # Pydantic制約を回避するため、プライベート属性として設定
        object.__setattr__(self, '_api_key', api_key)
        object.__setattr__(self, '_llm_type', llm_type)
        object.__setattr__(self, '_use_langfuse', use_langfuse)

        # ProductManagerインスタンスを作成
        object.__setattr__(self, '_product_center_agent_manager', ProductCenterAgentManager(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse
        ))

    def _run(self, command: str, llm_type: Optional[str] = None, session_id: Optional[str] = None, user_id: Optional[str] = None, is_entry_agent: Optional[bool] = False) -> str:
        """ProductCenterAgentManagerの処理を実行"""
        try:
            # ProductCenterAgentManagerに処理を委譲
            result = self._product_center_agent_manager.process_command(
                command=command,
                llm_type=llm_type,
                session_id=session_id,
                user_id=user_id,
                is_entry_agent=is_entry_agent
            )
            return result
        except Exception as e:
            return json.dumps({
                "error": f"ProductCenterAgentManager処理エラー: {str(e)}",
                "manager": "ProductCenterAgentManager"
            }, ensure_ascii=False)
