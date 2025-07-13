import json
from abc import abstractmethod, ABC
from typing import Type, Optional, Any
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from ai_agents.base_agent import BaseAgentState
from utils.string_utils import json_to_state


class BaseToolInput(BaseModel):
    """共通ツール入力スキーマ"""
    command: str = Field(description="command to execute")
    kwargs: Optional[dict] = Field(default=None, description="Additional keyword arguments for the command, you MUST put all of the parameters that you want to pass to the command here")
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
             shared_state: Optional[str] = None, **kwargs) -> BaseAgentState | str:
        """Agent command execution with proper error handling following LangChain patterns"""
        command_input = json.dumps({
            "command": command,
            "parameters": kwargs if kwargs else {}
        })

        result = None
        try:
            shared_state_object = json_to_state(shared_state, self.agent.get_state_class())
        except Exception as e:
            error_msg = f"エージェント「{self.agent.agent_name}」の共有状態変換中にエラーが発生しました: {str(e)}"
            print(f"❌ {error_msg}")
            return self._format_error_response("SHARED_STATE_ERROR", error_msg)

        try:
            # エージェントでコマンドを処理
            result = self.agent.process_command(
                command=command_input,
                user_input=user_input,
                session_id=session_id,
                user_id=user_id,
                is_entry_agent=is_entry_agent,
                shared_state=shared_state_object
            )

            # Check if the result contains an error response
            if self._is_error_response(result):
                print(f"⚠️ エージェント「{self.agent.agent_name}」がエラーレスポンスを返しました")
                return self._handle_agent_error_response(result)

            return result

        except Exception as e:
            error_msg = f"エージェント「{self.agent.agent_name}」がコマンド処理中にエラーが発生しました: {str(e)}"
            print(f"❌ {error_msg}")
            return self._format_error_response("COMMAND_EXECUTION_ERROR", error_msg)

    def _has_meaningful_error(self, error_value: Any) -> bool:
        """Check if an error value is meaningful (not null, not empty)"""
        if error_value is None:
            return False
        if isinstance(error_value, str) and error_value.strip() == "":
            return False
        if isinstance(error_value, dict) and not error_value:
            return False
        if isinstance(error_value, list) and not error_value:
            return False
        return True

    def _is_error_response(self, result: Any) -> bool:
        """Check if the agent result contains an error response"""
        if isinstance(result, dict):
            # Check for error in the result dictionary
            if "error" in result and self._has_meaningful_error(result["error"]):
                return True
            # Check for error in messages (if it's a BaseAgentState-like structure)
            if "messages" in result and isinstance(result["messages"], list):
                for message in result["messages"]:
                    if hasattr(message, 'content') and isinstance(message.content, str):
                        try:
                            content_dict = json.loads(message.content)
                            if isinstance(content_dict, dict) and "error" in content_dict and self._has_meaningful_error(content_dict["error"]):
                                return True
                        except (json.JSONDecodeError, TypeError):
                            # If content is not JSON, check for error keywords
                            if "error" in message.content.lower():
                                return True
        elif isinstance(result, str):
            # Check for error keywords in string response
            try:
                result_dict = json.loads(result)
                if isinstance(result_dict, dict) and "error" in result_dict and self._has_meaningful_error(result_dict["error"]):
                    return True
            except (json.JSONDecodeError, TypeError):
                # If not JSON, check for error keywords
                if "error" in result.lower():
                    return True
        return False

    def _handle_agent_error_response(self, result: Any) -> str:
        """Handle agent error response following LangChain tool error patterns"""
        error_info = self._extract_error_info(result)

        # Format the error response in a way that prevents repeated tool calls
        error_response = {
            "tool_error": True,
            "agent_name": self.agent.agent_name,
            "error_code": error_info.get("code", "AGENT_ERROR"),
            "error_message": error_info.get("message", "Agent returned an error response"),
            "original_result": str(result)
        }

        return json.dumps(error_response, ensure_ascii=False, indent=2)

    def _extract_error_info(self, result: Any) -> dict:
        """Extract error information from the agent result"""
        # Handle BaseAgentState-like dictionary responses
        if isinstance(result, dict):
            # Check for direct error field
            if "error" in result:
                error = result["error"]
                if isinstance(error, dict):
                    return {
                        "code": error.get("code", "UNKNOWN_ERROR"),
                        "message": error.get("message", "Unknown error occurred")
                    }
                else:
                    return {
                        "code": "UNKNOWN_ERROR",
                        "message": str(error)
                    }

            # Check for error_message field (BaseAgentState structure)
            if "error_message" in result and result["error_message"]:
                error_msg = result["error_message"]
                if isinstance(error_msg, dict):
                    return {
                        "code": error_msg.get("code", "AGENT_ERROR"),
                        "message": error_msg.get("message", str(error_msg))
                    }
                else:
                    return {
                        "code": "AGENT_ERROR",
                        "message": str(error_msg)
                    }

            # Check for error in the last AI message content
            if "messages" in result and isinstance(result["messages"], list):
                for message in reversed(result["messages"]):  # Check from last message
                    if hasattr(message, 'content') and isinstance(message.content, str):
                        try:
                            content_dict = json.loads(message.content)
                            if isinstance(content_dict, dict) and "error" in content_dict:
                                error = content_dict["error"]
                                if isinstance(error, dict):
                                    return {
                                        "code": error.get("code", "MESSAGE_ERROR"),
                                        "message": error.get("message", "Error in message content")
                                    }
                        except (json.JSONDecodeError, TypeError):
                            continue

            # Check for response_message field
            if "response_message" in result:
                try:
                    response_dict = json.loads(result["response_message"])
                    if isinstance(response_dict, dict) and "error" in response_dict:
                        return self._extract_error_info(response_dict)
                except (json.JSONDecodeError, TypeError):
                    pass

        elif isinstance(result, str):
            try:
                result_dict = json.loads(result)
                if isinstance(result_dict, dict) and "error" in result_dict:
                    return self._extract_error_info(result_dict)
            except (json.JSONDecodeError, TypeError):
                pass
            return {
                "code": "STRING_ERROR",
                "message": result
            }

        return {
            "code": "UNKNOWN_ERROR",
            "message": "Unknown error format"
        }

    def _format_error_response(self, error_code: str, error_message: str) -> str:
        """Format error response in a consistent way"""
        error_response = {
            "tool_error": True,
            "agent_name": self.agent.agent_name,
            "error_code": error_code,
            "error_message": error_message
        }

        return json.dumps(error_response, ensure_ascii=False, indent=2)

    async def _arun(self, command: str, user_input: Optional[str] = None, session_id: Optional[str] = None,
                    user_id: Optional[str] = None, is_entry_agent: Optional[bool] = False,
                    shared_state: Optional[str] = None, **kwargs) -> str:
        """エージェントコマンドを非同期実行"""
        # 非同期実行は同期実行と同じ処理を行う TODO: 実際の非同期処理を実装する
        return self._run(command, user_input, session_id, user_id, is_entry_agent, shared_state, **kwargs)
