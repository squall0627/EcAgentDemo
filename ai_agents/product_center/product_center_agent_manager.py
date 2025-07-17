from ai_agents.base_agent import BaseAgent
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.product_center.tools.product_detail_agent_tool import ProductDetailAgentTool
from ai_agents.product_center.tools.product_publish_agent_tool import ProductPublishAgentTool
from ai_agents.product_center.tools.product_tools import GenerateHtmlTool


class ProductCenterAgentManager(BaseAgent):
    """
       商品センター管理専門Manager - BaseAgentを継承したAgent Manager
       商品センター関連タスクを分析し、適切なAgentToolに自動ルーティング
       """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """ProductCenterAgentManager初期化"""
        super().__init__(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse,
            agent_name="ProductCenterAgentManager"
        )

    def _initialize_tools(self):
        """ProductCenterAgentManager用ツールを初期化"""
        return [ProductDetailAgentTool(api_key=self.api_key,
                                       llm_type=self.llm_type,
                                       use_langfuse=self.langfuse_handler.use_langfuse),
                ProductPublishAgentTool(api_key=self.api_key,
                                        llm_type=self.llm_type,
                                        use_langfuse=self.langfuse_handler.use_langfuse),
                GenerateHtmlTool(),]

    def _get_system_message_content(self, is_entry_agent: bool = False) -> str:
        """ProductCenterAgentManager system message content (dynamic generation)"""

        if is_entry_agent:
            # Entry agent case: Human-friendly natural language response
            return f"""
You are a specialized EC back-office product center management coordinator. You understand natural language commands from administrators and coordinate comprehensive product management functionality across multiple specialized agents while maximizing conversation history utilization.

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
You are a specialized product center management coordinator in a multi-layer agent system. You process structured commands from upstream agents, coordinate with downstream specialized agents, and return structured data for further processing.

## Your Purpose
    Execute product center management operations by coordinating downstream agents based on structured commands from upstream agents and return structured results.

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

Execute operations efficiently through coordinated agent management and try to return structured data if possible. If not, gather all results from the tools you used, summarize them clearly, and report the outcome to the upstream agent.
"""

    def _get_workflow_name(self) -> str:
        """ワークフロー名を取得"""
        return "ProductCenterAgentManager_Workflow"

    def get_agent_capability(self) -> AgentCapability:
        """ProductCenterAgentManager能力定義を取得"""
        return self._merge_downstream_agent_capabilities()

    # def process_command(self, command: str, user_input: str = None, llm_type: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False, shared_state: BaseAgentState = None) -> BaseAgentState:
    #     """
    #     商品センター管理コマンドを処理（多層Agent間状態互通対応）
    #
    #     Args:
    #         command: ユーザーコマンド
    #         user_input: ユーザーのオリジナル入力内容
    #         llm_type: LLMタイプ
    #         session_id: セッションID
    #         user_id: ユーザーID
    #         is_entry_agent: エントリーエージェントかどうか
    #         shared_state: 上流Agentから渡された共有状態（下流Agentの場合に使用）
    #
    #     Returns:
    #         BaseAgentState: エージェント実行結果の状態オブジェクト（多層Agent間での状態共有用）
    #     """
    #     # ProductManagementAgentに処理を委譲
    #     return ProductDetailAgent(
    #             api_key=self.api_key,
    #             llm_type=llm_type or self.llm_type,
    #             use_langfuse=True
    #         ).process_command(command, user_input, session_id=session_id, user_id=user_id, is_entry_agent=is_entry_agent, shared_state=shared_state)

if __name__ == "__main__":
    from httpx import AsyncClient
    import asyncio
    async def mulit_agent_chat_product_search():
        """测试商品搜索功能"""
        request_data = {
            "message": "Jancode 1000000000001の商品を検索してください",
            "session_id": "test_session_search_001",
            "user_id": "test_user_search",
            "llm_type": "ollama_qwen3"
        }

        async with AsyncClient() as client:
            response = await client.post(
                f"http://localhost:5004/api/agent/multi-agent/chat",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=600  # 设置超时时间为30秒
            )

            # assert response.status_code == 200
            response_data = response.json()

            print(response_data)

    asyncio.run(mulit_agent_chat_product_search())