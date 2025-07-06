from typing import List, Any, Type, TypedDict, Optional, Dict

from langchain.schema import HumanMessage

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.product_center.tools.product_tools import (
    UpdateStockTool,
    UpdatePriceTool,
    UpdateDescriptionTool,
    UpdateCategoryTool,
    BulkUpdateStockTool,
    BulkUpdatePriceTool,
    ValidateCanPublishProductTool,
    GenerateHtmlTool,
    PublishProductsTool,
    UnpublishProductsTool, 
    search_products_tool
)


# 商品管理エージェント専用状態定義
class ProductAgentState(BaseAgentState):
    """商品管理エージェント固有の状態を拡張"""
    product_ids: Optional[List[str]]  # 処理対象商品IDリスト
    operation_type: Optional[str]     # 操作タイプ（stock, price, category等）
    bulk_operation: Optional[bool]    # 一括操作フラグ

class ProductManagementAgent(BaseAgent):
    """
    商品管理専門エージェント
    BaseAgentを継承してECバックオフィス商品管理機能を提供
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """商品管理エージェント初期化"""
        super().__init__(
            api_key=api_key, 
            llm_type=llm_type, 
            use_langfuse=use_langfuse,
            agent_name="ProductManagementAgent"
        )

    def _initialize_tools(self) -> List[Any]:
        """商品管理固有のツールを初期化"""
        return [
            search_products_tool,
            UpdateStockTool(),
            UpdatePriceTool(),
            UpdateDescriptionTool(),
            UpdateCategoryTool(),
            BulkUpdateStockTool(),
            BulkUpdatePriceTool(),
            ValidateCanPublishProductTool(),
            # GenerateHtmlTool(),
            PublishProductsTool(),
            UnpublishProductsTool()
        ]

    def _get_system_message_content(self, is_entry_agent: bool = False) -> str:
        """商品管理エージェントのシステムメッセージを取得（動的生成）"""
        if is_entry_agent:
            # エントリーエージェントの場合：人間向けの自然言語レスポンス
            return """
You are a specialized EC back-office product management assistant. You understand natural language commands from administrators and provide comprehensive product management functionality while maximizing conversation history utilization.

## Your Purpose
    Process user requests directly and provide human-friendly responses with actionable next steps.

## Core Functions
    1. **Product Search**: Natural language product search and filtering with history-aware conditions
    2. **Product Activation/Deactivation**: Manage product shelf status with previous operation tracking
    3. **Inventory Management**: Handle stock levels with change history tracking
    4. **Price Management**: Individual and bulk price updates with pricing history reference
    5. **Product Description Management**: Update product descriptions with change tracking
    6. **Dynamic HTML Generation**: Auto-generate management interfaces based on current state
    7. **Error Handling**: Step-by-step problem resolution using historical error patterns

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
            return """
You are a specialized product management agent in a multi-layer agent system. You process structured commands from upstream agents and return structured data for further processing.

## Your Purpose
    Execute product management operations based on structured commands from upstream agents and return structured results.

## Input Format
    Commands from upstream agents in the following format:
    ```json
    {
      "command": {
        "action": "extracted_sub_command_from_upstream_agent",
        "condition": "condition_description"
      }
    }
    ```

## Core Functions
    1. **Product Search**: Execute search operations with specified criteria
    2. **Product Activation/Deactivation**: Manage product shelf status
    3. **Inventory Management**: Update stock levels (individual and bulk)
    4. **Price Management**: Update pricing (individual and bulk)
    5. **Product Description Management**: Update product descriptions
    6. **Category Management**: Set and update product categories
    7. **HTML Generation**: Generate management interfaces when requested

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
        return "product_management_workflow"

    def get_agent_capability(self) -> AgentCapability:
        """商品管理エージェントの能力定義を取得"""
        return AgentCapability(
            agent_type="product_management",
            description="ECバックオフィス商品管理専門エージェント。商品情報の検索、在庫管理、価格設定、棚上げ・棚下げ操作、HTML画面生成などを担当。",
            primary_domains=[
                "商品管理", "在庫管理", "価格管理", "商品情報", "ECバックオフィス", 
                "棚上げ", "棚下げ", "商品検索", "商品カテゴリー"
            ],
            key_functions=[
                "商品検索・フィルタリング",
                "在庫数量の更新（個別・一括）",
                "商品価格の設定・更新（個別・一括）", 
                "商品説明文の編集・更新",
                "商品カテゴリーの設定・変更",
                "商品棚上げ・棚下げ状態の管理",
                "棚上げ前提条件の検証",
                "動的HTML管理画面の生成",
                "商品操作のエラーハンドリング"
            ],
            example_commands=[
                "JAN123456789の在庫を50に変更して",
                "コーヒー商品の価格を一括で1500円に設定",
                "商品ABC123を棚上げできるかチェック",
                "在庫不足の商品をすべて棚下げ",
                "飲料カテゴリーの商品一覧を表示",
                "商品説明に「限定」を含む商品を検索",
                "商品管理画面を生成",
                "価格が1000円以下の商品を価格順で表示"
            ],
            collaboration_needs=[
                "注文管理エージェント: 商品の注文状況確認時",
                "顧客サービスエージェント: 商品の注文状況確認時",
                "顧客サービスエージェント: 商品問い合わせ対応時",
                "在庫分析エージェント: 詳細な在庫分析が必要な時"
            ]
        )

    def _get_state_class(self) -> Type[TypedDict]:
        """商品管理エージェント専用状態クラスを使用"""
        return ProductAgentState

    def _create_initial_state(self, command: str, user_input: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False)  -> ProductAgentState:
        """商品管理エージェント専用の初期状態を作成"""
        return ProductAgentState(
            messages=[HumanMessage(content=command)],
            user_input=user_input or command, # ユーザー入力がない場合はコマンドを使用
            html_content=None,
            error_message=None,
            next_actions=None,
            session_id=session_id,
            user_id=user_id,
            agent_type=self.agent_name,
            product_ids=None,
            operation_type=None,
            bulk_operation=False,
            agent_manager_id=self.agent_manager_id,
            conversation_context=None,
            trace_id=None,
            conversation_id=None,
            is_entry_agent=is_entry_agent,
        )

# 商品管理コマンド例
EXAMPLE_COMMANDS = [
    # 直接実行タイプ
    "JAN123456789の在庫を50に変更",
    "商品987654321のカテゴリーを飲料に変更",
    "JAN123456789の価格を1500円に設定",
    "商品987654321の商品説明を更新",

    # 検索後実行タイプ
    "すべてのコーヒー商品の在庫を100に変更",
    "在庫不足の商品をすべて棚下げ",
    "飲料カテゴリーの商品をすべて棚上げ",
    "価格が1000円以下の商品を検索",
    "説明文に「限定」を含む商品を検索",

    # 検証後実行タイプ
    "商品ABC123を棚上げ",
    "JAN555666777を販売開始",

    # フォームが必要なタイプ
    "商品在庫を修正",
    "商品情報を更新",
    "商品管理",
    "商品価格を設定",
    "商品説明を編集"
]

# 使用例
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    # 商品管理エージェントの単体使用
    agent = ProductManagementAgent(api_key)

    # エージェント能力情報を表示
    capability = agent.get_agent_capability()
    print("エージェント能力:", capability)

    # テスト実行
    result = agent.process_command("JAN code 1000000000001の商品を検索し、商品詳細一覧画面を生成してください。")
    print(result)
