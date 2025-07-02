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
        return """あなたは商品センター管理専門のAgentManagerです。
    
    ## 担当領域：
    - 商品検索・フィルタリング
    - 商品在庫管理
    - 商品価格管理
    - 商品棚上げ・棚下げ管理
    - 商品説明・カテゴリー管理
    
    ## 利用可能なAgentTool：
    - **product_management_agent**: 商品管理全般を実行する専門Agent
    
    ## 処理方針：
    1. ユーザーの商品管理要求を分析
    2. product_management_agentに適切な指示を与えて実行
    3. 実行結果を確認し、必要に応じて追加処理を指示
    4. 最終結果をユーザーに分かりやすく提示
    
    商品管理に関する全ての要求を効率的に処理し、高品質な結果を提供してください。"""

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