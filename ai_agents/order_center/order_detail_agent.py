from typing import List, Any, Type, TypedDict, Optional

from langchain.schema import HumanMessage

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.order_center.tools.order_tools import (
    GetOrderDetailTool,
    SearchOrdersTool
)


class OrderDetailAgentState(BaseAgentState):
    """注文詳細エージェント状態クラス"""
    pass


class OrderDetailAgent(BaseAgent):
    """
    注文詳細情報管理エージェント
    Order Detail Information Management Agent

    注文の詳細情報を取得・表示する専門エージェント
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """OrderDetailAgent初期化"""
        super().__init__(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse,
            agent_name="OrderDetailAgent"
        )

    def _initialize_tools(self):
        """OrderDetailAgent用ツールを初期化"""
        return [
            GetOrderDetailTool(),
            SearchOrdersTool()
        ]

    def _get_system_message_content(self, is_entry_agent: bool = False) -> str:
        """OrderDetailAgent system message content"""

        if is_entry_agent:
            return f"""
You are a specialized order detail management agent for an EC back-office system. You help administrators view and analyze detailed order information with comprehensive search capabilities.

## Your Purpose
    Process user requests for order detail information, provide comprehensive order data, and offer actionable insights for order management.

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

Always respond in friendly, clear Japanese while maximizing conversation history utilization to prioritize administrator workflow efficiency.
"""
        else:
            return f"""
You are a specialized order detail management agent in a multi-layer agent system. You process structured commands for order detail operations and return structured data.

## Your Purpose
    Execute order detail retrieval and search operations based on structured commands from upstream agents and return structured results.

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

Execute operations efficiently and try to return structured data if possible. If not, gather all results from the tools you used, summarize them clearly, and report the outcome to the upstream agent.
"""

    def _get_workflow_name(self) -> str:
        """ワークフロー名を取得"""
        return "OrderDetailAgent_Workflow"

    def get_agent_capability(self) -> AgentCapability:
        """OrderDetailAgent能力定義を取得"""
        return AgentCapability(
            agent_type="order_detail",
            description="Specialized agent for managing order detail information in the EC back office. Responsible for retrieving detailed order information, searching orders with various filters, and providing comprehensive order analysis.",
            primary_domains=[
                "Order Details", "Order Search", "Customer Information", "Order Status", "Order Items",
                "Payment Information", "Shipping Information"
            ],
            key_functions=[
                "Retrieve detailed order information by order ID",
                "Search orders with multiple filters (customer, status, amount, date)",
                "Display order status and progression tracking",
                "Analyze customer order history and patterns",
                "Show order item and pricing breakdown",
                "Provide order statistics and summaries"
            ],
            example_commands=[
                "注文ID ORD-12345678 の詳細情報を取得してください",
                "顧客名「田中」の注文を検索してください",
                "支払い済みの注文を表示してください",
                "金額が10000円以上の注文を検索",
                "今月の注文一覧を表示"
            ],
            collaboration_needs=[
                "Order Status Change Agent: When status updates are needed after viewing details",
                "Order Item Modification Agent: When item changes are required",
                "Order Cancellation Agent: When cancellation is needed after review"
            ]
        )

    def get_state_class(self) -> Type[BaseAgentState]:
        """状態クラスを取得"""
        return OrderDetailAgentState

    def _create_initial_state(self, command: str, user_input: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False) -> OrderDetailAgentState:
        """注文詳細エージェント専用の初期状態を作成"""
        return OrderDetailAgentState(
            messages=[HumanMessage(content=command)],
            user_input=user_input or command,
            html_content=None,
            error_message=None,
            next_actions=None,
            session_id=session_id,
            user_id=user_id,
            agent_type=self.agent_name,
            agent_manager_id=self.agent_manager_id,
            conversation_context=None,
            trace_id=None,
            conversation_id=None,
            is_entry_agent=is_entry_agent,
        )


def single_agent_chat_order_detail():
    """注文詳細エージェント単体テスト"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    agent = OrderDetailAgent(api_key=api_key, llm_type="openai_gpt4")

    # テストコマンド
    test_command = "注文ID ORD-12345678 の詳細情報を取得してください"

    result = agent.process_command(
        command=test_command,
        user_input=test_command,
        session_id="test_session_001",
        user_id="test_user",
        is_entry_agent=True
    )

    print("=== 注文詳細エージェントテスト結果 ===")
    print(f"Result: {result.result_data}")
    print(f"Error: {result.error_message}")


if __name__ == "__main__":
    single_agent_chat_order_detail()
