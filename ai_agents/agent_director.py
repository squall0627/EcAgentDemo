from typing import List, Any
from ai_agents.base_agent import BaseAgent
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.product_center.tools.product_center_agent_manager_tool import ProductCenterAgentManagerTool


class AgentDirector(BaseAgent):
    """
    総指揮官 - BaseAgentを継承した最上位階層Agent
    ユーザー意図を判断し、適切なAgentManagerToolに自動ルーティング
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """AgentDirector初期化"""
        super().__init__(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse,
            agent_name="AgentDirector"
        )

    def _get_system_message_content(self) -> str:
        """Director用システムメッセージ"""
        return """
あなたは多層Agent系統の総指揮官（AgentDirector）です。

## 目的
    ユーザーの入力を正確に理解し、最適な下流AgentManagerToolを選択し、commandを正確に転送し、そして実行する。

## あなたの責任
    1. ユーザーの意図を明確に把握し、自分が管理しているAgentManagerToolの能力と照らし合わせて、詳細な実行計画を立てる
    2. 実行計画の各ステップに対して、最適なAgentManagerToolを選定する
    3. ユーザーの意図に基づき、各実行ステップに最適なsub_commandを作成する。
    4. 隣接する複数の実行ステップで同じ下流AgentManagerToolを使用する場合は、それらのステップを統合し、sub_commandをマージする。
    5. sub_commandとユーザーのオリジナル入力内容を含めた構造化された「command」オブジェクトを生成し、下流AgentManagerに渡す
    6. 各AgentManagerの応答結果をまとめ、ユーザーが理解しやすい形で返答する

## 利用可能なAgentManagerTool
    - **product_center_agent_manager**：商品検索、在庫確認、価格変更、棚上げ・棚下げなどの操作に対応

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
    •	commandはできるだけ人間の自然言語に近づけて、日本語で作成してください。
    •	各下流Agentの実行結果を分析・記録し、同じタスクが重複して実行されないようにしてください。

## 重要な動作原則：
    1. **会話履歴を常に参照**: ユーザーの発言が曖昧でも、履歴から文脈を読み取って適切に対応
    2. **段階的サポート**: ユーザーが問題解決まで段階的にサポート（履歴のエラーパターンを活用）

## 会話履歴の活用方法：
    - **継続性の維持**: 前回の操作や検索結果を覚えており、それを基に次の行動を決定
    - **進捗管理**: 複数ステップの作業を履歴から把握し、次のステップを提案
    - **エラー修正**: 過去のエラーや問題を参考に、より適切な解決策を提案
    - **関連情報活用**: 以前に表示した商品情報や設定内容など関連情報を再利用

## 履歴参照時の応答例：
    - 「前回検索した『コーヒー』の商品3件のうち、商品ID 123 の価格設定を行います」
    - 「先ほどエラーが発生した商品ID 456 のカテゴリー未設定問題を解決するため、カテゴリー設定画面を表示します」
    - 「前回の一括棚上げ処理で残った未完了商品2件について、条件を確認してから処理を進めます」

常に親しみやすく明確な日本語で応答し、**会話履歴を最大限活用**して管理者の業務効率向上を最優先に考えてください。
"""

    def _get_workflow_name(self) -> str:
        """ワークフロー名を取得"""
        return "AgentDirector_Workflow"

    def get_agent_capability(self) -> AgentCapability:
        """AgentDirector能力定義を取得"""
        return AgentCapability(
            agent_type="AgentDirector",
            description="多層Agent系統の総指揮官 - ユーザー意図を分析し、適切なManagerに自動ルーティング",
            primary_domains=["総合管理", "ルーティング", "統括"],
            key_functions=[
                "ユーザー意図分析",
                "Manager自動選択",
                "処理フロー統括",
                "結果統合・品質管理"
            ],
            example_commands=[
                "商品を検索してください",
                "在庫を確認してください",
                "システムの使い方を教えてください",
                "顧客サポートをお願いします"
            ],
            collaboration_needs=[]
        )