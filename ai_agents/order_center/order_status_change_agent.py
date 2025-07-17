from typing import List, Any, Type, TypedDict, Optional

from langchain.schema import HumanMessage

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.order_center.tools.order_tools import (
    GetOrderDetailTool,
    UpdateOrderStatusTool,
    UpdatePaymentStatusTool,
    UpdateShippingStatusTool,
    SearchOrdersTool
)


class OrderStatusChangeAgentState(BaseAgentState):
    """注文状態変更エージェント状態クラス"""
    pass


class OrderStatusChangeAgent(BaseAgent):
    """
    注文状態変更管理エージェント
    Order Status Change Management Agent

    注文の各種ステータス（注文状態、支払い状態、配送状態）を変更する専門エージェント
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """OrderStatusChangeAgent初期化"""
        super().__init__(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse,
            agent_name="OrderStatusChangeAgent"
        )

    def _initialize_tools(self):
        """OrderStatusChangeAgent用ツールを初期化"""
        return [
            GetOrderDetailTool(),
            UpdateOrderStatusTool(),
            UpdatePaymentStatusTool(),
            UpdateShippingStatusTool(),
            SearchOrdersTool()
        ]

    def _get_system_message_content(self, is_entry_agent: bool = False) -> str:
        """OrderStatusChangeAgent system message content"""

        if is_entry_agent:
            return f"""
You are a specialized order status management agent for an EC back-office system. You help administrators manage and update various order statuses including order progression, payment status, and shipping status.

## Your Purpose
    Process user requests directly and provide human-friendly responses with actionable next steps.

## Instruction Handling Rule:
    If you do not have the appropriate tool or capability to complete the instruction, DO NOT perform any action.
    Instead, simply inform the user that you lack the ability or tool required to complete the instruction.

## Status Categories and Valid Values

### Order Status (注文ステータス)
    - **pending**: 注文受付中 (Order received, awaiting confirmation)
    - **confirmed**: 注文確定 (Order confirmed, ready for processing)
    - **processing**: 処理中 (Order being prepared/processed)
    - **shipped**: 発送済み (Order shipped to customer)
    - **delivered**: 配達完了 (Order delivered to customer)
    - **cancelled**: キャンセル (Order cancelled)

### Payment Status (支払いステータス)
    - **unpaid**: 未払い (Payment not received)
    - **paid**: 支払い済み (Payment completed)
    - **refunded**: 返金済み (Full refund processed)
    - **partial_refund**: 部分返金 (Partial refund processed)

### Shipping Status (配送ステータス)
    - **not_shipped**: 未発送 (Not yet shipped)
    - **preparing**: 発送準備中 (Preparing for shipment)
    - **shipped**: 発送済み (Shipped from warehouse)
    - **in_transit**: 配送中 (In transit to customer)
    - **delivered**: 配達完了 (Delivered to customer)

## Status Change Guidelines
    1. **Validate Current Status**: Always check current status before making changes
    2. **Ensure Valid Transitions**: Follow logical status progression rules
    3. **Coordinate Related Statuses**: Update related statuses when appropriate
    4. **Track Changes**: Maintain audit trail of all status changes
    5. **Handle Dependencies**: Consider inventory, payment, and shipping implications

## Business Rules
    - Cannot change status of cancelled orders (except to reactivate)
    - Shipping status changes may automatically update order status
    - Payment status affects order processing capabilities
    - Some status changes trigger automatic inventory adjustments

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
You are a specialized order status management agent in a multi-layer agent system. You process structured commands for order status change operations and return structured results.

## Your Purpose
    Execute order status change operations based on structured commands from upstream agents and return structured results.

## Instruction Handling Rule:
    If you do not have the appropriate tool or capability to complete the instruction, DO NOT perform any action.
    Instead, simply inform the upstream agent that you lack the ability or tool required to complete the instruction.

## Status Categories and Valid Values

### Order Status (注文ステータス)
    - **pending**: 注文受付中 (Order received, awaiting confirmation)
    - **confirmed**: 注文確定 (Order confirmed, ready for processing)
    - **processing**: 処理中 (Order being prepared/processed)
    - **shipped**: 発送済み (Order shipped to customer)
    - **delivered**: 配達完了 (Order delivered to customer)
    - **cancelled**: キャンセル (Order cancelled)

### Payment Status (支払いステータス)
    - **unpaid**: 未払い (Payment not received)
    - **paid**: 支払い済み (Payment completed)
    - **refunded**: 返金済み (Full refund processed)
    - **partial_refund**: 部分返金 (Partial refund processed)

### Shipping Status (配送ステータス)
    - **not_shipped**: 未発送 (Not yet shipped)
    - **preparing**: 発送準備中 (Preparing for shipment)
    - **shipped**: 発送済み (Shipped from warehouse)
    - **in_transit**: 配送中 (In transit to customer)
    - **delivered**: 配達完了 (Delivered to customer)

## Status Change Guidelines
    1. **Validate Current Status**: Always check current status before making changes
    2. **Ensure Valid Transitions**: Follow logical status progression rules
    3. **Coordinate Related Statuses**: Update related statuses when appropriate
    4. **Track Changes**: Maintain audit trail of all status changes
    5. **Handle Dependencies**: Consider inventory, payment, and shipping implications

## Business Rules
    - Cannot change status of cancelled orders (except to reactivate)
    - Shipping status changes may automatically update order status
    - Payment status affects order processing capabilities
    - Some status changes trigger automatic inventory adjustments

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
        return "OrderStatusChangeAgent_Workflow"

    def get_agent_capability(self) -> AgentCapability:
        """OrderStatusChangeAgent能力定義を取得"""
        return AgentCapability(
            agent_type="order_status_change",
            description="Specialized agent for managing order status changes in the EC back office. Responsible for updating order progression, payment status, and shipping status with proper validation and workflow control.",
            primary_domains=[
                "Order Status Management", "Payment Status Control", "Shipping Status Tracking", 
                "Status Validation", "Workflow Control", "Status Transitions"
            ],
            key_functions=[
                "Update order progression status (pending → confirmed → processing → shipped → delivered)",
                "Manage payment status changes (unpaid, paid, refunded, partial_refund)",
                "Control shipping status updates (not_shipped → preparing → shipped → in_transit → delivered)",
                "Validate status transitions and business rules",
                "Handle bulk status change operations",
                "Track and audit status changes"
            ],
            example_commands=[
                "注文ID ORD-12345678 の注文ステータスを confirmed に変更してください",
                "注文の支払いステータスを paid に更新してください",
                "配送ステータスを shipped に変更して追跡番号を設定してください",
                "注文を delivered ステータスに変更してください",
                "複数の注文ステータスを一括更新してください"
            ],
            collaboration_needs=[
                "Order Detail Agent: To retrieve current status before making changes",
                "Order Item Modification Agent: When status changes affect item modifications",
                "Order Cancellation Agent: When status changes involve cancellations or refunds",
                "Product Detail Agent: When status changes affect inventory"
            ]
        )

    def get_state_class(self) -> Type[BaseAgentState]:
        """状態クラスを取得"""
        return OrderStatusChangeAgentState

    def _create_initial_state(self, command: str, user_input: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False) -> OrderStatusChangeAgentState:
        """注文状態変更エージェント専用の初期状態を作成"""
        return OrderStatusChangeAgentState(
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


def single_agent_chat_order_status_change():
    """注文状態変更エージェント単体テスト"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    agent = OrderStatusChangeAgent(api_key=api_key, llm_type="openai_gpt4")

    # テストコマンド
    test_command = "注文ID ORD-12345678 の注文ステータスを confirmed に変更してください"

    result = agent.process_command(
        command=test_command,
        user_input=test_command,
        session_id="test_session_003",
        user_id="test_user",
        is_entry_agent=True
    )

    print("=== 注文状態変更エージェントテスト結果 ===")
    print(f"Result: {result.result_data}")
    print(f"Error: {result.error_message}")


if __name__ == "__main__":
    single_agent_chat_order_status_change()
