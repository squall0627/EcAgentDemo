from typing import List, Any, Type, TypedDict, Optional

from langchain.schema import HumanMessage

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.product_center.tools.product_tools import (
    ValidateCanPublishProductTool,
    PublishProductsTool,
    UnpublishProductsTool,
    search_products_tool
)


# 商品棚上げ・棚下げ管理エージェント専用状態定義
class ProductPublishAgentState(BaseAgentState):
    """商品棚上げ・棚下げ管理エージェント固有の状態を拡張"""
    jancodes: Optional[List[str]]  # 処理対象商品Jancodeリスト
    operation_type: Optional[str]     # 操作タイプ（publish, unpublish, validate等）
    bulk_operation: Optional[bool]    # 一括操作フラグ

class ProductPublishAgent(BaseAgent):
    """
    商品棚上げ・棚下げ管理専門エージェント
    BaseAgentを継承してECバックオフィス商品棚上げ・棚下げ機能を提供
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """商品棚上げ・棚下げ管理エージェント初期化"""
        super().__init__(
            api_key=api_key, 
            llm_type=llm_type, 
            use_langfuse=use_langfuse,
            agent_name="ProductPublishAgent"
        )

    def _initialize_tools(self) -> List[Any]:
        """商品棚上げ・棚下げ管理固有のツールを初期化"""
        return [
            search_products_tool,
            ValidateCanPublishProductTool(),
            PublishProductsTool(),
            UnpublishProductsTool(),
        ]

    def _get_system_message_content(self, is_entry_agent: bool = False) -> str:
        """商品棚上げ・棚下げ管理エージェントのシステムメッセージを取得（動的生成）"""
        if is_entry_agent:
            # エントリーエージェントの場合：人間向けの自然言語レスポンス
            return f"""
You are a specialized EC back-office product publish/unpublish management assistant. You understand natural language commands from administrators and provide comprehensive product shelving management functionality while maximizing conversation history utilization.

## Your Purpose
    Process user requests directly and provide human-friendly responses with actionable next steps.

## Available tools
{self._generate_tool_descriptions}

## Response Format
    - Structured JSON response
    - Include "html_content" field for direct screen rendering when needed
    - Include "error" field for error messages in Japanese
    - Include "next_actions" field for suggested next steps (considering conversation history)

## Conversation History Usage
    - **Continuity**: Remember previous operations and search results for informed decision-making
    - **Context understanding**: Interpret ambiguous expressions like "that product", "previous results", "last search"
    - **Progress tracking**: Understand multi-step workflows from history and suggest next steps
    - **Error correction**: Reference past errors to provide better solutions
    - **Information reuse**: Leverage previously displayed product information and settings

Always respond in friendly, clear Japanese while maximizing conversation history utilization to prioritize administrator workflow efficiency.
"""
        else:
            # 非エントリーエージェントの場合：上流Agent向けの構造化レスポンス
            return f"""
You are a specialized product publish/unpublish management agent in a multi-layer agent system. You process structured commands from upstream agents and return structured data for further processing.

## Your Purpose
    Execute product publish/unpublish operations based on structured commands from upstream agents and return structured results.

## Available tools
{self._generate_tool_descriptions}

## Response Format
    - Structured JSON response optimized for upstream agent consumption
    - Include "html_content" field when HTML generation is requested (return raw HTML without parsing)
    - Focus on data accuracy and structured output for agent-to-agent communication

## Error Handling
    - Return structured error information in "error" field
    - Provide actionable error details for upstream agent processing
    - Maintain operation continuity when possible

Execute operations efficiently and return structured results optimized for multi-agent workflow processing.
"""

    def _get_workflow_name(self) -> str:
        """ワークフロー名を取得"""
        return "product_publish_workflow"

    def get_agent_capability(self) -> AgentCapability:
        """商品棚上げ・棚下げ管理エージェントの能力定義を取得"""
        return AgentCapability(
            agent_type="product_publish",
            description="Specialized agent for managing product publishing and unpublishing operations in the EC (e-commerce) back office. Responsible for tasks such as product search, publish validation, shelf activation, and shelf deactivation.",
            primary_domains=[
                "Product Publishing", "Product Shelving", "Shelf Management", "Product Search", "Publish Validation",
                "Product Activation", "Product Deactivation"
            ],
            key_functions=[
                "Search and filter products",
                "Validate product publishing prerequisites",
                "Publish products to shelf (single or bulk)",
                "Unpublish products from shelf (single or bulk)",
                "Handle errors during publish/unpublish operations"
            ],
            example_commands=[
                "JAN123456789を棚上げして",
                "コーヒー商品を一括で棚上げ",
                "商品ABC123を棚上げできるかチェック",
                "在庫不足の商品をすべて棚下げ",
                "飲料カテゴリーの商品一覧を表示",
            ],
            collaboration_needs=[
                "Order Management Agent: When checking the order status of products",
                "Customer Service Agent: When responding to order-related inquiries",
                "Customer Service Agent: When handling product-related inquiries",
                "Product Detail Agent: When detailed product information updates are required"
            ]
        )

    def get_state_class(self) -> Type[TypedDict]:
        """商品棚上げ・棚下げ管理エージェント専用状態クラスを使用"""
        return ProductPublishAgentState

    def _create_initial_state(self, command: str, user_input: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False)  -> ProductPublishAgentState:
        """商品棚上げ・棚下げ管理エージェント専用の初期状態を作成"""
        return ProductPublishAgentState(
            messages=[HumanMessage(content=command)],
            user_input=user_input or command, # ユーザー入力がない場合はコマンドを使用
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
            jancodes=None,
            operation_type=None,
            bulk_operation=False,
        )

# 商品棚上げ・棚下げ管理コマンド例
EXAMPLE_COMMANDS = [
    # 直接実行タイプ
    "JAN123456789を棚上げ",
    "商品987654321を棚下げ",
    "JAN123456789の棚上げ条件をチェック",
    "商品987654321を販売開始",

    # 検索後実行タイプ
    "すべてのコーヒー商品を棚上げ",
    "在庫不足の商品をすべて棚下げ",
    "飲料カテゴリーの商品をすべて棚上げ",
    "価格が1000円以下の商品を検索",
    "説明文に「限定」を含む商品を検索",

    # 検証後実行タイプ
    "商品ABC123を棚上げできるかチェック",
    "JAN555666777を販売開始",

    # フォームが必要なタイプ
    "商品を棚上げ",
    "商品を棚下げ",
    "商品棚上げ・棚下げ管理",
    "商品公開設定",
    "商品販売停止"
]

# 使用例
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    # 商品棚上げ・棚下げ管理エージェントの単体使用
    agent = ProductPublishAgent(api_key)

    # エージェント能力情報を表示
    capability = agent.get_agent_capability()
    print("エージェント能力:", capability)

    # テスト実行
    result = agent.process_command("JAN code 1000000000001の商品を検索し、棚上げ条件をチェックしてください。")
    print(result)