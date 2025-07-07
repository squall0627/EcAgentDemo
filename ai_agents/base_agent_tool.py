from abc import abstractmethod, ABC
from typing import Type, Optional, Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ai_agents.base_agent import BaseAgentState
from utils.string_utils import json_to_state


class BaseToolInput(BaseModel):
    """共通ツール入力スキーマ"""
    command: str = Field(description="command to execute")
    user_input: Optional[str] = Field(default=None, description="User input (optional)")
    session_id: Optional[str] = Field(default=None, description="Session ID (optional)")
    user_id: Optional[str] = Field(default=None, description="User ID (optional)")
    is_entry_agent: Optional[bool] = Field(default=False, description="Entry agent flag")
    shared_state: Optional[str] = Field(default=None,
                                        description="Shared state for agent processing (optional)")


class BaseAgentTool(BaseTool, ABC):
    """
    Base Agent Tool
    Inherits from LangChain's BaseTool to provide common functionality for agent tools
    """

    name: str = "base_agent_tool"
    description: str = "Base agent tool for executing commands"
    args_schema: Type[BaseModel] = BaseToolInput
    agent: Any = Field(default=None, exclude=True)  # Exclude from serialization

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """Base agent tool initialization"""
        super().__init__()
        self.agent = self._initialize_agent(api_key, llm_type, use_langfuse)
        self.description = self._get_agent_description()

    @abstractmethod
    def _initialize_agent(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """Initialize the agent with the provided parameters"""
        raise NotImplementedError("Subclasses must implement this method")

    def _get_agent_description(self) -> str:
        """Get agent description formatted for LLM tool consumption"""
        try:
            capability = self.agent.get_agent_capability()
            return capability.format_for_llm_tool_description()
        except Exception as e:
            raise Exception(f"Error occurred while getting agent description: {str(e)}") from e

    def _run(self, command: str, user_input: Optional[str] = None, session_id: Optional[str] = None,
             user_id: Optional[str] = None, is_entry_agent: Optional[bool] = False,
             shared_state: Optional[str] = None) -> BaseAgentState | str:
        """Agent command execution"""
        result = None
        try:
            shared_state_object = json_to_state(shared_state, self.agent.get_state_class())
            # エージェントでコマンドを処理
            result = self.agent.process_command(
                command=command,
                user_input=user_input,
                session_id=session_id,
                user_id=user_id,
                is_entry_agent=is_entry_agent,
                shared_state=shared_state_object
            )
            return result
        except Exception as e:
            if not result:
                result = shared_state or f"エージェント「{self.agent.agent_name}」がコマンド処理中にエラーが発生しました: {str(e)}"
            if isinstance(result, dict):
                result.error_message = f"エージェント「{self.agent.agent_name}」がコマンド処理中にエラーが発生しました: {str(e)}"
            return result

    async def _arun(self, command: str, user_input: Optional[str] = None, session_id: Optional[str] = None,
                    user_id: Optional[str] = None, is_entry_agent: Optional[bool] = False,
                    shared_state: Optional[str] = None) -> str:
        """エージェントコマンドを非同期実行"""
        # 非同期実行は同期実行と同じ処理を行う TODO: 実際の非同期処理を実装する
        return self._run(command, user_input, session_id, user_id, is_entry_agent, shared_state)
