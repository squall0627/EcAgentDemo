from typing import List, Any, Type, TypedDict, Optional

from langchain.schema import HumanMessage

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.order_center.tools.order_tools import (
    GetOrderDetailTool,
    CreateOrderTool,
    CancelOrderTool,
    SearchOrdersTool
)


class OrderItemModificationAgentState(BaseAgentState):
    """注文商品変更エージェント状態クラス"""
    pass


class OrderItemModificationAgent(BaseAgent):
    """
    注文商品変更管理エージェント
    Order Item Modification Management Agent

    注文の商品内容を変更する専門エージェント
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """OrderItemModificationAgent初期化"""
        super().__init__(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse,
            agent_name="OrderItemModificationAgent"
        )

    def _initialize_tools(self):
        """OrderItemModificationAgent用ツールを初期化"""
        return [
            GetOrderDetailTool(),
            CreateOrderTool(),
            CancelOrderTool(),
            SearchOrdersTool()
        ]

    def _get_system_message_content(self, is_entry_agent: bool = False) -> str:
        """OrderItemModificationAgent system message content"""

        if is_entry_agent:
            return f"""
You are a specialized order item modification agent for an EC back-office system. You help administrators modify order contents including adding, removing, or changing quantities of items in existing orders.

## Your Purpose
Process user requests for order item modifications, guide through the modification process, and ensure proper handling of inventory and pricing updates.

## Core Capabilities
- **Order Item Analysis**: Analyze current order items and identify modification requirements
- **Modification Guidance**: Guide users through the order modification process
- **Inventory Validation**: Check product availability for item additions or quantity increases
- **Price Recalculation**: Ensure proper pricing when items are modified
- **Order Recreation**: Handle complex modifications by creating new orders when necessary

## Available Tools
{self.generate_tool_descriptions()}

## Modification Process Guidelines
1. **Analyze Current Order**: Always retrieve current order details first
2. **Validate Changes**: Check inventory and pricing for requested modifications
3. **Determine Approach**: Decide between direct modification or order recreation
4. **Execute Changes**: Implement the modification using appropriate tools
5. **Confirm Results**: Verify the modification was successful

## Important Notes
- For complex modifications, may need to cancel original order and create new one
- Always check inventory availability before adding items or increasing quantities
- Recalculate totals including taxes and shipping when items change
- Maintain audit trail of all modifications
- Consider order status when determining if modifications are allowed

## Response Guidelines
- Clearly explain the modification process to users
- Provide step-by-step guidance for complex changes
- Alert users to any limitations based on order status
- Use clear, professional Japanese for communication
- Always confirm changes before execution

Prioritize accuracy and proper inventory management when handling order modifications.
"""
        else:
            return f"""
You are a specialized order item modification agent in a multi-layer agent system. You process structured commands for order item modification operations and return structured results.

## Your Purpose
Execute order item modification operations based on structured commands from upstream agents and return structured results.

## Available Tools
{self.generate_tool_descriptions()}

## Response Format
- Structured JSON response optimized for upstream agent consumption
- Include modification results with before/after comparison
- Provide error information in structured format when issues occur
- Focus on data accuracy and structured output for agent-to-agent communication

Execute order item modification operations efficiently and return comprehensive structured data.
"""

    def _get_workflow_name(self) -> str:
        """ワークフロー名を取得"""
        return "OrderItemModificationAgent_Workflow"

    def get_agent_capability(self) -> AgentCapability:
        """OrderItemModificationAgent能力定義を取得"""
        return AgentCapability(
            agent_type="order_item_modification",
            description="Specialized agent for modifying order item contents in the EC back office. Responsible for adding, removing, or changing quantities of items in existing orders with proper inventory and pricing management.",
            primary_domains=[
                "Order Item Management", "Inventory Validation", "Price Recalculation", "Order Recreation",
                "Item Addition/Removal", "Quantity Modification"
            ],
            key_functions=[
                "Add new items to existing orders",
                "Remove items from orders",
                "Change quantities of ordered items",
                "Validate inventory availability for modifications",
                "Recalculate pricing after item changes",
                "Handle order recreation for complex modifications",
                "Analyze modification impact on orders"
            ],
            example_commands=[
                "注文ID ORD-12345678 に商品JANコード 1000000000002 を1個追加してください",
                "注文ORD-87654321から商品を1つ削除してください",
                "注文の商品数量を3個に変更してください",
                "注文内容を変更して価格を再計算してください",
                "商品を別の商品に変更してください"
            ],
            collaboration_needs=[
                "Order Detail Agent: To retrieve current order information before modifications",
                "Order Status Change Agent: To update order status after modifications",
                "Product Detail Agent: To validate product availability and pricing",
                "Order Cancellation Agent: When order recreation requires cancellation"
            ]
        )

    def get_state_class(self) -> Type[BaseAgentState]:
        """状態クラスを取得"""
        return OrderItemModificationAgentState

    def _create_initial_state(self, command: str, user_input: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False) -> OrderItemModificationAgentState:
        """注文商品変更エージェント専用の初期状態を作成"""
        return OrderItemModificationAgentState(
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


def single_agent_chat_order_item_modification():
    """注文商品変更エージェント単体テスト"""
    import os
    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    agent = OrderItemModificationAgent(api_key=api_key, llm_type="openai_gpt4")

    # テストコマンド
    test_command = "注文ID ORD-12345678 に商品JANコード 1000000000002 を1個追加してください"

    result = agent.process_command(
        command=test_command,
        user_input=test_command,
        session_id="test_session_002",
        user_id="test_user",
        is_entry_agent=True
    )

    print("=== 注文商品変更エージェントテスト結果 ===")
    print(f"Result: {result.result_data}")
    print(f"Error: {result.error_message}")


if __name__ == "__main__":
    single_agent_chat_order_item_modification()
