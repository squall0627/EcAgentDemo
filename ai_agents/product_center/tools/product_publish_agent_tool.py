from typing import Type, Optional
from pydantic import BaseModel, Field

from ai_agents.base_agent_tool import BaseToolInput, BaseAgentTool
from ai_agents.product_center.product_publish_agent import ProductPublishAgent


class ProductPublishToolInput(BaseToolInput):
    """商品棚上げ・棚下げ管理ツール入力スキーマ"""
    command: str = Field(description="Product publish/unpublish management command to execute")
    kwargs: Optional[dict] = Field(default=None, description="Additional keyword arguments for the command, you MUST put all of the parameters that you want to pass to the command here")
    user_input: Optional[str] = Field(default=None, description="User input (optional)")
    session_id: Optional[str] = Field(default=None, description="Session ID (optional)")
    user_id: Optional[str] = Field(default=None, description="User ID (optional)")
    is_entry_agent: Optional[bool] = Field(default=False, description="Entry agent flag")
    shared_state: Optional[str] = Field(default=None,
                                        description="Shared state for agent processing (optional)")


class ProductPublishAgentTool(BaseAgentTool):
    """
    Product Publish/Unpublish Management Agent Tool
    Inherits from LangChain's BaseTool to provide EC back office product publish/unpublish management functionality
    """

    name: str = "product_publish_agent_tool"
    description: str = "Product publish/unpublish management agent tool for executing commands"
    args_schema: Type[BaseModel] = ProductPublishToolInput

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """商品棚上げ・棚下げ管理エージェントツール初期化"""
        super().__init__(api_key=api_key, llm_type=llm_type, use_langfuse=use_langfuse)
        inside_tools_description = self.agent.generate_tool_descriptions()
        self.description = f"Product detail management agent tool for executing commands. This agent has the following tools: {inside_tools_description}"

    def _initialize_agent(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """Initialize the ProductPublishAgent with the provided parameters"""
        return ProductPublishAgent(api_key, llm_type, use_langfuse)
