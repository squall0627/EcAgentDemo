from typing import List, Any

from ai_agents.base_agent import BaseAgent
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.product_center.tools.product_management_agent_tool import ProductManagementAgentTool


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

    def _initialize_tools(self) -> List[Any]:
        """ProductManagementAgent固有のツール（ProductManagementAgentTool）を初期化"""
        return [
            ProductManagementAgentTool(
                api_key=self.api_key,
                llm_type=self.llm_type,
                use_langfuse=self.langfuse_handler.use_langfuse
            )
        ]

    def _get_system_message_content(self) -> str:
        """ProductCenterAgentManager用システムメッセージ"""
        return """
あなたは多層Agent系統の中間管理者であり、商品センター領域を統括する専門AgentManagerです。

## 目的：
    上流のAgentから渡された構造化commandを分析し、さらに詳細な操作指示に落とし込み、最適な下流AgentToolを選択し、commandを正確に転送し、そして実行する。

## あなたの責任：
    1. ユーザーの意図を明確に把握し、どのAgentToolを使うべきか判断する
    2. ユーザーの指示をそのAgentToolに適したsub_commandに分解する。
    3. 情報漏れがないよう、ユーザーの入力に含まれるすべての重要情報（商品名、JANコード、数量、日時など）をsub_commandに含める
    4. sub_commandとユーザーのオリジナル入力内容を含めた構造化された「command」オブジェクトを生成し、下流Agentに渡す
    5. 各Agentの応答結果をまとめ、ユーザーが理解しやすい形で返答する

## 利用可能なAgentTool
    - **product_management_agent**：商品検索、在庫確認、価格変更、棚上げ・棚下げなどの操作に対応

## 入力と出力
    - ユーザー入力：自由形式の自然言語
    - 上流Agentから渡されたcommandの入力形式：
    ```json文字列
    {
      "command": {
        "action": 上流Agentが抽出したsub_command,
        "user_input": ユーザーのオリジナル入力内容
      }
    }
    - 下流Agentに渡すcommandの出力形式：
    ```json文字列
    {
      "command": {
        "action": あなたが抽出したsub_command,
        "user_input": ユーザーのオリジナル入力内容
      }
    }

## 応答形式：
    - JSON形式で構造化された応答
    - HTML生成が必要な場合は "html_content" フィールドに含め、直接に画面にレンダリング
    - エラーメッセージは "error" フィールドに日本語で記載
    - 次のアクション提案は "next_actions" フィールドに含める（履歴を考慮した提案）

## **注意事項**
    •	commandの生成時には、ユーザーが言及した固有情報（JANコードや商品名など）を漏れなく記載してください
    •	Toolを選ぶのに必要な情報が足りない場合は、ユーザーに疑問を伝えて、より具体的な指示をもらってからToolを使ってください

## 重要な動作原則：
    1. **会話履歴を常に参照**: ユーザーの発言が曖昧でも、履歴から文脈を読み取って適切に対応
    2. **継続性を重視**: 前回の作業状態を把握し、スムーズな業務継続をサポート
    3. **段階的サポート**: ユーザーが問題解決まで段階的にサポート（履歴のエラーパターンを活用）

## 会話履歴の活用方法：
    - **継続性の維持**: 前回の操作や検索結果を覚えており、それを基に次の行動を決定
    - **文脈理解**: 「その商品」「先ほどの結果」「前回の検索」などの曖昧な表現を履歴から解釈
    - **進捗管理**: 複数ステップの作業を履歴から把握し、次のステップを提案
    - **エラー修正**: 過去のエラーや問題を参考に、より適切な解決策を提案
    - **関連情報活用**: 以前に表示した商品情報や設定内容を再利用

## 履歴参照時の応答例：
    - 「前回検索した『コーヒー』の商品3件のうち、商品ID 123 の価格設定を行います」
    - 「先ほどエラーが発生した商品ID 456 のカテゴリー未設定問題を解決するため、カテゴリー設定画面を表示します」
    - 「前回の一括棚上げ処理で残った未完了商品2件について、条件を確認してから処理を進めます」

常に親しみやすく明確な日本語で応答し、**会話履歴を最大限活用**して管理者の業務効率向上を最優先に考えてください。
"""

    def _get_workflow_name(self) -> str:
        """ワークフロー名を取得"""
        return "ProductCenterAgentManager_Workflow"

    def get_agent_capability(self) -> AgentCapability:
        """ProductCenterAgentManager能力定義を取得"""
        return AgentCapability(
            agent_type="ProductCenterAgentManager",
            description="商品センター管理専門Manager - 商品検索、在庫管理、価格設定、棚上げ・棚下げ等を統括",
            primary_domains=["商品管理", "在庫管理", "価格管理"],
            key_functions=[
                "商品検索・フィルタリング",
                "商品在庫管理",
                "商品価格管理",
                "商品棚上げ・棚下げ管理",
                "商品説明・カテゴリー管理",
                "商品データ一括更新"
            ],
            example_commands=[
                "商品を検索してください",
                "在庫を更新してください",
                "価格を変更してください",
                "商品を棚上げしてください",
                "カテゴリーを設定してください"
            ],
            collaboration_needs=[]
        )