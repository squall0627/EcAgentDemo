from ai_agents.base_agent import BaseAgent
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.order_center.tools.order_detail_agent_tool import OrderDetailAgentTool
from ai_agents.order_center.tools.order_item_modification_agent_tool import OrderItemModificationAgentTool
from ai_agents.order_center.tools.order_status_change_agent_tool import OrderStatusChangeAgentTool
from ai_agents.order_center.tools.order_cancellation_agent_tool import OrderCancellationAgentTool


class OrderCenterAgentManager(BaseAgent):
    """
       注文センター管理専門Manager - BaseAgentを継承したAgent Manager
       注文センター関連タスクを分析し、適切なAgentToolに自動ルーティング
       """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """OrderCenterAgentManager初期化"""
        super().__init__(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse,
            agent_name="OrderCenterAgentManager"
        )

    def _initialize_tools(self):
        """OrderCenterAgentManager用ツールを初期化"""
        return [
            OrderDetailAgentTool(
                api_key=self.api_key,
                llm_type=self.llm_type,
                use_langfuse=self.langfuse_handler.use_langfuse
            ),
            OrderItemModificationAgentTool(
                api_key=self.api_key,
                llm_type=self.llm_type,
                use_langfuse=self.langfuse_handler.use_langfuse
            ),
            OrderStatusChangeAgentTool(
                api_key=self.api_key,
                llm_type=self.llm_type,
                use_langfuse=self.langfuse_handler.use_langfuse
            ),
            OrderCancellationAgentTool(
                api_key=self.api_key,
                llm_type=self.llm_type,
                use_langfuse=self.langfuse_handler.use_langfuse
            )
        ]

    def _get_system_message_content(self, is_entry_agent: bool = False) -> str:
        """OrderCenterAgentManager system message content (dynamic generation)"""

        if is_entry_agent:
            # Entry agent case: Human-friendly natural language response
            return f"""
You are a specialized EC back-office order center management coordinator. You understand natural language commands from administrators and coordinate comprehensive order management functionality across multiple specialized agents while maximizing conversation history utilization.

## Your Purpose
    Process user requests directly, coordinate with downstream agents, and return structured JSON responses with actionable next steps.

## Instruction Handling Rule:
    If you do not have the appropriate tool or capability to complete the instruction, DO NOT perform any action.
    Instead, simply inform the user that you lack the ability or tool required to complete the instruction.

## Response Format
    - Structured JSON response
    - Include "html_content" field for direct screen rendering when needed
    - Include "error" field for error messages in Japanese
    - Include "next_actions" field for suggested next steps (considering conversation history)
        * Type: string (single action) OR array of strings (multiple actions)

## Conversation History Usage
    - **Continuity**: Remember previous operations and search results for informed decision-making
    - **Context understanding**: Interpret ambiguous expressions like "that product", "previous results", "last search"
    - **Progress tracking**: Understand multi-step workflows from history and suggest next steps
    - **Error correction**: Reference past errors to provide better solutions
    - **Information reuse**: Leverage previously displayed product information and settings

Always respond in friendly, clear Japanese while **maximizing conversation history utilization** to prioritize administrator workflow efficiency.
"""
        else:
            # Non-entry agent case: Structured response for upstream agents
            return f"""
You are a specialized order center management coordinator in a multi-layer agent system. You process structured commands from upstream agents, coordinate with downstream specialized agents, and return structured data for further processing.

## Your Purpose
    Execute order center management operations by coordinating downstream agents based on structured commands from upstream agents and return structured results.

## Instruction Handling Rule:
    If you do not have the appropriate tool or capability to complete the instruction, DO NOT perform any action.
    Instead, simply inform the upstream agent that you lack the ability or tool required to complete the instruction.

## Response Format
    - Structured JSON response optimized for upstream agent consumption
    - Include "html_content" field when HTML generation is requested (return raw HTML without parsing)
    - Focus on data accuracy and structured output for agent-to-agent communication

## Error Handling
    - Return structured error information in "error" field
    - Provide actionable error details for upstream agent processing
    - Maintain operation continuity when possible

Execute order management operations efficiently through coordinated agent management and try to return structured data if possible. If not, gather all results from the tools you used, summarize them clearly, and report the outcome to the upstream agent.
"""

    def _get_workflow_name(self) -> str:
        """ワークフロー名を取得"""
        return "OrderCenterAgentManager_Workflow"

    def get_agent_capability(self) -> AgentCapability:
        """OrderCenterAgentManager能力定義を取得"""
        return self._merge_downstream_agent_capabilities()


if __name__ == "__main__":
    from httpx import AsyncClient
    import asyncio
    
    async def multi_agent_chat_order_search():
        """注文検索機能テスト"""
        request_data = {
            "message": "注文ID ORD-12345678 の詳細情報を取得してください",
            "session_id": "test_session_order_001",
            "user_id": "test_user_order",
            "llm_type": "ollama_qwen3"
        }

        async with AsyncClient() as client:
            response = await client.post(
                f"http://localhost:5004/api/agent/multi-agent/chat",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=600  # 設定超時時間為600秒
            )

            # assert response.status_code == 200
            response_data = response.json()

            print(response_data)

    asyncio.run(multi_agent_chat_order_search())