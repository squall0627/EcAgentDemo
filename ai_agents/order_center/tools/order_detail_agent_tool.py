from typing import Type, Optional
from pydantic import BaseModel, Field

from ai_agents.base_agent_tool import BaseAgentTool, BaseToolInput
from ai_agents.order_center.order_detail_agent import OrderDetailAgent


class OrderDetailToolInput(BaseToolInput):
    """注文詳細情報管理ツール入力スキーマ"""
    command: str = Field(description="Order detail management command to execute")
    user_input: Optional[str] = Field(default=None, description="User input (optional)")
    session_id: Optional[str] = Field(default=None, description="Session ID (optional)")
    user_id: Optional[str] = Field(default=None, description="User ID (optional)")
    is_entry_agent: Optional[bool] = Field(default=False, description="Entry agent flag")
    shared_state: Optional[str] = Field(default=None,
                                        description="Shared state for agent processing (optional)")


class OrderDetailAgentTool(BaseAgentTool):
    """
    Order Detail Management Agent Tool
    Inherits from LangChain's BaseTool to provide EC back office order detail management functionality
    """

    name: str = "order_detail_agent_tool"
    description: str = "Order detail management agent tool for executing commands"
    args_schema: Type[BaseModel] = OrderDetailToolInput

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """注文詳細情報管理エージェントツール初期化"""
        super().__init__(api_key=api_key, llm_type=llm_type, use_langfuse=use_langfuse)

    def _initialize_agent(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """Initialize the OrderDetailAgent with the provided parameters"""
        return OrderDetailAgent(api_key, llm_type, use_langfuse)