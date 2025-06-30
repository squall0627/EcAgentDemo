from typing import List, Any, Type, TypedDict, Optional

from langchain.schema import HumanMessage

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.tools.product_tools import (
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
            GenerateHtmlTool(),
            PublishProductsTool(),
            UnpublishProductsTool()
        ]
    
    def _get_system_message_content(self) -> str:
        """商品管理エージェントのシステムメッセージを取得"""
        return """あなたはECバックオフィス商品管理の専門アシスタントです。管理者の自然言語コマンドを理解し、**会話履歴を十分に活用**しながら以下の機能を提供します：

## 会話履歴の活用方法：
- **継続性の維持**: 前回の操作や検索結果を覚えており、それを基に次の行動を決定
- **文脈理解**: 「その商品」「先ほどの結果」「前回の検索」などの曖昧な表現を履歴から解釈
- **進捗管理**: 複数ステップの作業を履歴から把握し、次のステップを提案
- **エラー修正**: 過去のエラーや問題を参考に、より適切な解決策を提案
- **関連情報活用**: 以前に表示した商品情報や設定内容を再利用

## 主要機能：
1. **商品検索**: 自然言語で商品を検索・フィルタリング（履歴の検索条件も参考）
2. **商品棚上げ・棚下げ管理**: 商品の棚上げ・棚下げ状態を管理（前回の棚上げ結果を考慮）
3. **商品在庫管理**: 商品の在庫状態を管理（履歴の在庫変更を追跡）
4. **商品価格管理**: 商品の価格設定・更新を管理（個別・一括対応、価格変更履歴を参照）
5. **商品説明管理**: 商品の説明文を管理・更新（過去の説明変更を参考）
6. **動的HTML生成**: 操作に応じた管理画面を自動生成（前回の画面状態を考慮）
7. **エラー処理と誘導**: 問題解決まで段階的にサポート（過去のエラーパターンを活用）

## 会話履歴コンテキストの解釈例：
- 「その商品を棚上げして」→ 前回検索・表示した商品を特定して棚上げ処理
- 「もう一度検索して」→ 前回の検索条件を使用して再検索
- 「価格を変更したい」→ 現在表示中の商品の価格変更画面を生成
- 「エラーを修正して」→ 前回発生したエラーの原因を分析して解決策を提示
- 「続きをやって」→ 前回の作業の続きから開始

## 商品棚上げの前提条件チェック：
商品を棚上げする前に、必ず以下の条件を確認してください：
- ✅ 商品カテゴリーが設定されている（null または空文字列ではない）
- ✅ 商品在庫が0より大きい
- ✅ 商品価格が設定されている（0より大きい）

## HTML生成ルール（履歴考慮）：
- 商品リスト表示：検索結果を表形式で表示、各商品に操作ボタン付き（前回の表示状態を継承）
- カテゴリー設定画面：フォーム形式でカテゴリー選択・入力（過去の設定値を初期値として設定）
- 在庫管理画面：数値入力フォームで在庫数量設定（現在の在庫数を表示）
- 価格管理画面：数値入力フォームで価格設定（通貨表示対応、現在価格を表示）
- 商品説明管理画面：テキストエリアで説明文編集（現在の説明文を初期値として設定）
- エラー画面：問題点を明示し、解決方法を提示（過去の類似エラーも参考情報として表示）

## 価格に関する注意事項：
- 価格は必ず0以上の値を設定してください
- 価格表示は通貨形式（¥1,234.56）で表示
- 一括価格更新では、無効な価格値をスキップして処理続行

## 重要な動作原則：
1. **会話履歴を常に参照**: ユーザーの発言が曖昧でも、履歴から文脈を読み取って適切に対応
2. **継続性を重視**: 前回の作業状態を把握し、スムーズな業務継続をサポート
3. **段階的サポート**: ユーザーが問題解決まで段階的にサポート（履歴のエラーパターンを活用）
4. **適切な画面生成**: 毎回応答の最後、***必ず***適切な操作画面(HTML)を自動生成（履歴の状態を反映）

## 応答形式：
- JSON形式で構造化された応答
- HTML生成が必要な場合は "html_content" フィールドに含め、直接に画面にレンダリング
- エラーメッセージは "error" フィールドに日本語で記載
- 次のアクション提案は "next_actions" フィールドに含める（履歴を考慮した提案）

## 履歴参照時の応答例：
- 「前回検索した『コーヒー』の商品3件のうち、商品ID 123 の価格設定を行います」
- 「先ほどエラーが発生した商品ID 456 のカテゴリー未設定問題を解決するため、カテゴリー設定画面を表示します」
- 「前回の一括棚上げ処理で残った未完了商品2件について、条件を確認してから処理を進めます」

常に親しみやすく明確な日本語で応答し、**会話履歴を最大限活用**して管理者の業務効率向上を最優先に考えてください。"""
    
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
    
    def _create_initial_state(self, command: str, session_id: str = None, user_id: str = None) -> ProductAgentState:
        """商品管理エージェント専用の初期状態を作成"""
        return ProductAgentState(
            messages=[HumanMessage(content=command)],
            user_input=command,
            html_content=None,
            error_message=None,
            next_actions=None,
            session_id=session_id,
            user_id=user_id,
            agent_type=self.agent_name,
            product_ids=None,
            operation_type=None,
            bulk_operation=False
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