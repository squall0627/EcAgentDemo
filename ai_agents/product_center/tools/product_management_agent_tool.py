import json
from typing import Optional, Type
from pydantic import BaseModel, Field

from langchain.tools import BaseTool

from ai_agents.product_center.product_management_agent import ProductManagementAgent

class AgentToolInput(BaseModel):
    """Agent Tool用の入力スキーマ"""
    command: str = Field(description="実行するコマンド")
    user_input: str = Field(default=None, description="ユーザーのオリジナル入力内容")
    llm_type: Optional[str] = Field(default=None, description="使用するLLMのタイプ")
    session_id: Optional[str] = Field(default=None, description="セッションID")
    user_id: Optional[str] = Field(default=None, description="ユーザーID")
    is_entry_agent: Optional[bool] = Field(default=False, description="エージェントとしてのエントリーかどうか")


class ProductManagementAgentTool(BaseTool):
    """
    ProductManagementAgentをTool化したクラス
    ProductManagerAgentから呼び出される商品管理実行ツール
    """
    name: str = "product_management_agent"
    description: str = "商品管理実行Agent - 具体的な商品管理タスクを実行（商品検索、商品在庫参照・更新、商品価格参照・更新、商品説明参照・更新、棚上げ・棚下げ等）"
    args_schema: Type[BaseModel] = AgentToolInput

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        super().__init__()
        # Pydantic制約を回避するため、プライベート属性として設定
        object.__setattr__(self, '_api_key', api_key)
        object.__setattr__(self, '_llm_type', llm_type)
        object.__setattr__(self, '_use_langfuse', use_langfuse)

        # ProductManagementAgentインスタンスを作成
        object.__setattr__(self, '_product_agent', ProductManagementAgent(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse
        ))

    def _run(self, command: str, user_input: Optional[str] = None, llm_type: Optional[str] = None, session_id: Optional[str] = None, user_id: Optional[str] = None, is_entry_agent: Optional[bool] = False) -> str:
        """ProductManagementAgentの処理を実行"""
        try:
            # ProductManagementAgentに処理を委譲
            result = self._product_agent.process_command(
                command=command,
                user_input=user_input,
                llm_type=llm_type,
                session_id=session_id,
                user_id=user_id,
                is_entry_agent=is_entry_agent
            )
            return result
        except Exception as e:
            return json.dumps({
                "error": f"ProductManagementAgent処理エラー: {str(e)}",
                "agent": "ProductManagementAgent"
            }, ensure_ascii=False)
