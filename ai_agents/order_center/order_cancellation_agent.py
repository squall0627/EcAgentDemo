from typing import List, Any, Type, TypedDict, Optional

from langchain.schema import HumanMessage

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.order_center.tools.order_tools import (
    GetOrderDetailTool,
    CancelOrderTool,
    UpdateOrderStatusTool,
    UpdatePaymentStatusTool,
    SearchOrdersTool
)


class OrderCancellationAgentState(BaseAgentState):
    """注文取消・返品エージェント状態クラス"""
    pass


class OrderCancellationAgent(BaseAgent):
    """
    注文取消・返品管理エージェント
    Order Cancellation and Return Management Agent

    注文のキャンセルや返品処理を行う専門エージェント
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """OrderCancellationAgent初期化"""
        super().__init__(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse,
            agent_name="OrderCancellationAgent"
        )

    def _initialize_tools(self):
        """OrderCancellationAgent用ツールを初期化"""
        return [
            GetOrderDetailTool(),
            CancelOrderTool(),
            UpdateOrderStatusTool(),
            UpdatePaymentStatusTool(),
            SearchOrdersTool()
        ]

    def _get_system_message_content(self, is_entry_agent: bool = False) -> str:
        """OrderCancellationAgent system message content"""

        if is_entry_agent:
            return f"""
You are a specialized order cancellation and return management agent for an EC back-office system. You help administrators handle order cancellations, returns, and refund processes with proper inventory and financial management.

## Your Purpose
    Process user requests directly and return structured JSON responses with actionable next steps.

## Instruction Handling Rule:
    If you do not have the appropriate tool or capability to complete the instruction, DO NOT perform any action.
    Instead, simply inform the user that you lack the ability or tool required to complete the instruction.

## Business Rule:
    - Check order status before allowing cancellation (CAN NOT cancel shipped/delivered orders without return process)

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
You are a specialized order cancellation and return management agent in a multi-layer agent system. You process structured commands for order cancellation and return operations and return structured results.

## Your Purpose
    Execute order cancellation and return operations based on structured commands from upstream agents and return structured results.

## Instruction Handling Rule:
    If you do not have the appropriate tool or capability to complete the instruction, DO NOT perform any action.
    Instead, simply inform the upstream agent that you lack the ability or tool required to complete the instruction.

## Business Rule:
    - Check order status before allowing cancellation (CAN NOT cancel shipped/delivered orders without return process)

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
        return "OrderCancellationAgent_Workflow"

    def get_agent_capability(self) -> AgentCapability:
        """OrderCancellationAgent能力定義を取得"""
        return AgentCapability(
            agent_type="order_cancellation",
            description="Specialized agent for handling order cancellations and returns in the EC back office. Responsible for processing cancellation requests, managing returns, handling refunds, and restoring inventory with proper policy enforcement.",
            primary_domains=[
                "Order Cancellation", "Return Processing", "Refund Management", "Inventory Restoration",
                "Policy Enforcement", "Payment Status Updates"
            ],
            key_functions=[
                "Cancel orders with automatic inventory restoration",
                "Process customer return requests and validation",
                "Calculate and process full and partial refunds",
                "Update payment status for refunded orders",
                "Manage inventory restoration after cancellations",
                "Enforce cancellation and return policy rules",
                "Handle bulk cancellation operations"
            ],
            example_commands=[
                "注文ID ORD-12345678 をキャンセルして、在庫を復元してください",
                "注文の返品処理を行ってください",
                "注文をキャンセルして返金処理をしてください",
                "複数の注文を一括キャンセルしてください",
                "返品された商品の在庫を復元してください"
            ],
            collaboration_needs=[
                "Order Detail Agent: To retrieve order information before cancellation",
                "Order Status Change Agent: To update order and payment status during cancellation",
                "Product Detail Agent: To restore inventory after cancellation",
                "Order Item Modification Agent: When partial cancellations require item modifications"
            ]
        )

    def get_state_class(self) -> Type[BaseAgentState]:
        """状態クラスを取得"""
        return OrderCancellationAgentState

    def _create_initial_state(self, command: str, user_input: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False) -> OrderCancellationAgentState:
        """注文取消・返品エージェント専用の初期状態を作成"""
        return OrderCancellationAgentState(
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


def single_agent_chat_order_cancellation():
    """注文取消・返品エージェント単体テスト"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    agent = OrderCancellationAgent(api_key=api_key, llm_type="openai_gpt4")

    # テストコマンド
    test_command = "注文ID ORD-12345678 をキャンセルして、在庫を復元してください"

    result = agent.process_command(
        command=test_command,
        user_input=test_command,
        session_id="test_session_004",
        user_id="test_user",
        is_entry_agent=True
    )

    print("=== 注文取消・返品エージェントテスト結果 ===")
    print(f"Result: {result.result_data}")
    print(f"Error: {result.error_message}")


if __name__ == "__main__":
    single_agent_chat_order_cancellation()
