from typing import Type, Optional
from pydantic import BaseModel, Field

from ai_agents.base_agent_tool import BaseAgentTool, BaseToolInput
from ai_agents.product_center.product_detail_agent import ProductDetailAgent


class ProductDetailToolInput(BaseToolInput):
    """商品詳細情報管理ツール入力スキーマ"""
    command: str = Field(description="Product detail management command to execute")
    kwargs: Optional[dict] = Field(default=None, description="Additional keyword arguments for the command, you MUST put all of the parameters that you want to pass to the command here")
    user_input: Optional[str] = Field(default=None, description="User input (optional)")
    session_id: Optional[str] = Field(default=None, description="Session ID (optional)")
    user_id: Optional[str] = Field(default=None, description="User ID (optional)")
    is_entry_agent: Optional[bool] = Field(default=False, description="Entry agent flag")
    shared_state: Optional[str] = Field(default=None,
                                        description="Shared state for agent processing (optional)")


class ProductDetailAgentTool(BaseAgentTool):
    """
    Product Detail Management Agent Tool
    Inherits from LangChain's BaseTool to provide EC back office product detail management functionality
    """

    name: str = "product_detail_agent_tool"
    description: str = "Product detail management agent tool for executing commands"
    args_schema: Type[BaseModel] = ProductDetailToolInput

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """商品詳細情報管理エージェントツール初期化"""
        super().__init__(api_key=api_key, llm_type=llm_type, use_langfuse=use_langfuse)
        inside_tools_description = self.agent.generate_tool_descriptions()
        self.description = f"Product detail management agent tool for executing commands. This agent has the following tools: {inside_tools_description}"

    def _initialize_agent(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """Initialize the ProductDetailAgent with the provided parameters"""
        return ProductDetailAgent(api_key, llm_type, use_langfuse)
