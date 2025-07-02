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

    def _initialize_tools(self) -> List[Any]:
        """Director固有のツール（各種ManagerTool）を初期化"""
        return [
            ProductCenterAgentManagerTool(
                api_key=self.api_key,
                llm_type=self.llm_type,
                use_langfuse=self.langfuse_handler.use_langfuse
            )
        ]

    def _get_system_message_content(self) -> str:
        """Director用システムメッセージ"""
        return """あなたは多層Agent系統の総指揮官（AgentDirector）です。

## 主要責任：
1. ユーザーの意図を分析・理解
2. 適切なAgentManagerToolを選択・実行
3. 全体的な処理フローを統括
4. 最終結果の統合・品質管理

## 利用可能なAgentManagerTool：
- **product_center_agent_manager**: 商品センター管理関連（商品検索、在庫管理、価格設定、棚上げ・棚下げ等）

適切なAgentManagerToolを選択し、ユーザーの要求を効率的に処理してください。
各AgentManagerToolの実行結果を適切に解釈し、ユーザーに分かりやすい形で回答してください。"""

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