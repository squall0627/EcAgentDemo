import os
import json
from typing import Dict, List, Any

from dotenv import load_dotenv

from ai_agents.base_agent import IntelligentMultiAgentOrchestrator
from ai_agents.product_management_agent import ProductManagementAgent
from ai_agents.intelligent_agent_router import RoutingDecision

load_dotenv()

class ECBackofficeMultiAgentManager:
    """
    ECバックオフィス用インテリジェントマルチエージェント統合管理クラス
    LLMベースの知的ルーティングで複数エージェントを統合管理
    """
    
    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """
        ECバックオフィス用インテリジェントマルチエージェント管理初期化
        
        Args:
            api_key: APIキー
            llm_type: デフォルトLLMタイプ
            use_langfuse: Langfuse使用フラグ
        """
        self.api_key = api_key
        self.default_llm_type = llm_type
        self.use_langfuse = use_langfuse
        
        # インテリジェントマルチエージェント統合管理を初期化
        self.orchestrator = IntelligentMultiAgentOrchestrator(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse
        )
        
        # 各種エージェントを初期化・登録
        self._initialize_agents()
    
    def _initialize_agents(self):
        """各種エージェントを初期化・登録"""
        
        # 商品管理エージェントを登録
        product_agent = ProductManagementAgent(
            api_key=self.api_key,
            llm_type=self.default_llm_type,
            use_langfuse=self.use_langfuse
        )
        
        self.orchestrator.register_agent(
            agent_type="product_management",
            agent=product_agent
        )
        
        # 将来的な他のエージェント登録予定箇所
        # self._register_order_management_agent()     # 注文管理エージェント
        # self._register_customer_service_agent()     # 顧客サービスエージェント
        # self._register_inventory_analysis_agent()   # 在庫分析エージェント
        # self._register_marketing_agent()            # マーケティングエージェント
    
    def _register_order_management_agent(self):
        """注文管理エージェント登録（将来実装予定）"""
        # TODO: 注文管理エージェントの実装
        # order_agent = OrderManagementAgent(
        #     api_key=self.api_key,
        #     llm_type=self.default_llm_type,
        #     use_langfuse=self.use_langfuse
        # )
        # self.orchestrator.register_agent(
        #     agent_type="order_management",
        #     agent=order_agent
        # )
        pass
    
    def _register_customer_service_agent(self):
        """顧客サービスエージェント登録（将来実装予定）"""
        # TODO: 顧客サービスエージェントの実装
        # customer_agent = CustomerServiceAgent(
        #     api_key=self.api_key,
        #     llm_type=self.default_llm_type,
        #     use_langfuse=self.use_langfuse
        # )
        # self.orchestrator.register_agent(
        #     agent_type="customer_service",
        #     agent=customer_agent
        # )
        pass
    
    def _register_inventory_analysis_agent(self):
        """在庫分析エージェント登録（将来実装予定）"""
        # TODO: 在庫分析エージェントの実装
        # inventory_agent = InventoryAnalysisAgent(
        #     api_key=self.api_key,
        #     llm_type=self.default_llm_type,
        #     use_langfuse=self.use_langfuse
        # )
        # self.orchestrator.register_agent(
        #     agent_type="inventory_analysis",
        #     agent=inventory_agent
        # )
        pass
    
    def _register_marketing_agent(self):
        """マーケティングエージェント登録（将来実装予定）"""
        # TODO: マーケティングエージェントの実装
        # marketing_agent = MarketingAgent(
        #     api_key=self.api_key,
        #     llm_type=self.default_llm_type,
        #     use_langfuse=self.use_langfuse
        # )
        # self.orchestrator.register_agent(
        #     agent_type="marketing",
        #     agent=marketing_agent
        # )
        pass
    
    def process_command(self, command: str, agent_type: str = None, llm_type: str = None, 
                       session_id: str = None, user_id: str = None, context: Dict[str, Any] = None) -> str:
        """
        インテリジェントルーティング対応の統一コマンド処理インターフェース
        
        Args:
            command: ユーザーコマンド
            agent_type: 指定エージェントタイプ（省略時はインテリジェントルーティング）
            llm_type: LLMタイプ（省略時はデフォルト）
            session_id: セッションID
            user_id: ユーザーID
            context: 追加コンテキスト情報
            
        Returns:
            str: JSON形式のレスポンス（ルーティング情報含む）
        """
        return self.orchestrator.process_command(
            command=command,
            agent_type=agent_type,
            context=context,
            llm_type=llm_type,
            session_id=session_id,
            user_id=user_id
        )
    
    def process_collaborative_command(self, command: str, context: Dict[str, Any] = None, 
                                    llm_type: str = None, session_id: str = None, user_id: str = None) -> str:
        """
        複数エージェント連携が必要なコマンドを処理
        
        Args:
            command: ユーザーコマンド
            context: 追加コンテキスト情報
            llm_type: LLMタイプ
            session_id: セッションID
            user_id: ユーザーID
            
        Returns:
            str: JSON形式のレスポンス
        """
        return self.orchestrator.process_collaborative_command(
            command=command,
            context=context,
            llm_type=llm_type,
            session_id=session_id,
            user_id=user_id
        )
    
    def analyze_command_routing(self, command: str, context: Dict[str, Any] = None) -> RoutingDecision:
        """
        コマンドのルーティング分析を実行（実際の処理は行わない）
        
        Args:
            command: ユーザーコマンド
            context: 追加コンテキスト情報
            
        Returns:
            RoutingDecision: ルーティング決定結果
        """
        return self.orchestrator.route_command_intelligently(command, context)
    
    def get_available_agents(self) -> List[str]:
        """利用可能なエージェントタイプのリストを取得"""
        return list(self.orchestrator.agents.keys())
    
    def get_agent_info(self, agent_type: str = None) -> Dict[str, Any]:
        """エージェント情報を取得"""
        if agent_type:
            agent = self.orchestrator.get_agent(agent_type)
            return agent.get_agent_info() if agent else {}
        else:
            return self.orchestrator.get_all_agents_info()
    
    def get_agent_capabilities(self) -> Dict[str, Dict[str, Any]]:
        """全エージェントの能力情報を取得"""
        capabilities = {}
        for agent_type, agent in self.orchestrator.agents.items():
            capability = agent.get_agent_capability()
            capabilities[agent_type] = {
                "description": capability.description,
                "primary_domains": capability.primary_domains,
                "key_functions": capability.key_functions,
                "example_commands": capability.example_commands,
                "collaboration_needs": capability.collaboration_needs or []
            }
        return capabilities
    
    def switch_llm_for_agent(self, agent_type: str, new_llm_type: str) -> bool:
        """指定エージェントのLLMを切り替え"""
        agent = self.orchestrator.get_agent(agent_type)
        if agent:
            agent.switch_llm(new_llm_type)
            return True
        return False
    
    def switch_routing_llm(self, new_llm_type: str) -> bool:
        """ルーティング用LLMを切り替え"""
        try:
            self.orchestrator.intelligent_router.llm_handler.switch_llm(new_llm_type)
            self.orchestrator.intelligent_router.routing_llm = (
                self.orchestrator.intelligent_router.llm_handler.get_llm()
            )
            return True
        except Exception:
            return False
    
    def get_routing_analytics(self) -> Dict[str, Any]:
        """ルーティング分析情報を取得"""
        return self.orchestrator.get_routing_analytics()
    
    def provide_routing_feedback(self, command: str, actual_agent: str, success: bool, user_feedback: str = None):
        """
        ルーティング結果のフィードバックを提供
        
        Args:
            command: 元のコマンド
            actual_agent: 実際に使用されたエージェント
            success: 処理成功フラグ
            user_feedback: ユーザーフィードバック
        """
        self.orchestrator.provide_routing_feedback(command, actual_agent, success, user_feedback)
    
    def get_system_status(self) -> Dict[str, Any]:
        """システム全体の状態を取得"""
        routing_analytics = self.get_routing_analytics()
        
        return {
            "available_agents": self.get_available_agents(),
            "total_agents": len(self.orchestrator.agents),
            "agent_capabilities": self.get_agent_capabilities(),
            "routing_analytics": routing_analytics,
            "system_health": {
                "agents_registered": len(self.orchestrator.agents),
                "routing_history_count": routing_analytics.get("total_routings", 0),
                "high_confidence_rate": routing_analytics.get("high_confidence_rate", 0.0),
                "collaboration_requests": routing_analytics.get("collaboration_requests", 0)
            }
        }
    
    def simulate_routing(self, test_commands: List[str]) -> Dict[str, Any]:
        """
        テストコマンドでルーティングをシミュレーション
        
        Args:
            test_commands: テストコマンドリスト
            
        Returns:
            Dict[str, Any]: シミュレーション結果
        """
        simulation_results = []
        
        for command in test_commands:
            routing_decision = self.analyze_command_routing(command)
            simulation_results.append({
                "command": command,
                "selected_agent": routing_decision.selected_agent,
                "confidence": routing_decision.confidence,
                "confidence_level": routing_decision.confidence_level.value,
                "reasoning": routing_decision.reasoning,
                "alternative_agents": routing_decision.alternative_agents,
                "requires_collaboration": routing_decision.requires_collaboration,
                "collaboration_sequence": routing_decision.collaboration_sequence
            })
        
        # 統計情報を計算
        total_commands = len(simulation_results)
        confidence_distribution = {}
        agent_distribution = {}
        
        for result in simulation_results:
            confidence_level = result["confidence_level"]
            agent = result["selected_agent"]
            
            confidence_distribution[confidence_level] = confidence_distribution.get(confidence_level, 0) + 1
            agent_distribution[agent] = agent_distribution.get(agent, 0) + 1
        
        return {
            "simulation_results": simulation_results,
            "statistics": {
                "total_commands": total_commands,
                "confidence_distribution": confidence_distribution,
                "agent_distribution": agent_distribution,
                "average_confidence": sum(r["confidence"] for r in simulation_results) / total_commands if total_commands > 0 else 0,
                "collaboration_required": sum(1 for r in simulation_results if r["requires_collaboration"])
            }
        }

# 使用例とテスト
if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    
    # インテリジェントマルチエージェント管理を初期化
    manager = ECBackofficeMultiAgentManager(api_key)
    
    # システム状態を表示
    print("=== システム状態 ===")
    status = manager.get_system_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    
    # エージェント能力情報を表示
    print("\n=== エージェント能力情報 ===")
    capabilities = manager.get_agent_capabilities()
    for agent_type, capability in capabilities.items():
        print(f"\n{agent_type}:")
        print(f"  説明: {capability['description']}")
        print(f"  主要ドメイン: {', '.join(capability['primary_domains'])}")
        print(f"  主要機能: {', '.join(capability['key_functions'][:3])}...")  # 最初の3つだけ表示
    
    # インテリジェントルーティングテスト
    print("\n=== インテリジェントルーティングテスト ===")
    test_commands = [
        "商品在庫を確認したい",
        "JAN123456789の価格を1500円に変更",
        "棚上げ商品の一覧を表示",
        "コーヒー商品の在庫を一括で100に設定",
        "商品管理画面を生成してください",
        "在庫不足の商品をすべて棚下げして",
        "商品ABC123を棚上げできるかチェック"
    ]
    
    # ルーティングシミュレーション
    simulation = manager.simulate_routing(test_commands)
    print(f"シミュレーション結果 (テストコマンド数: {simulation['statistics']['total_commands']}):")
    print(f"平均信頼度: {simulation['statistics']['average_confidence']:.2f}")
    print(f"エージェント分布: {simulation['statistics']['agent_distribution']}")
    print(f"信頼度分布: {simulation['statistics']['confidence_distribution']}")
    
    # 実際のコマンド処理テスト
    print("\n=== 実際のコマンド処理テスト ===")
    test_command = "JAN code 1000000000001の商品を検索し、商品詳細一覧画面を生成してください"
    
    print(f"処理コマンド: {test_command}")
    
    # まずルーティング分析
    routing_decision = manager.analyze_command_routing(test_command)
    print(f"選択エージェント: {routing_decision.selected_agent}")
    print(f"信頼度: {routing_decision.confidence:.2f} ({routing_decision.confidence_level.value})")
    print(f"選択理由: {routing_decision.reasoning}")
    
    # 実際の処理実行
    result = manager.process_command(test_command)
    response = json.loads(result)
    print(f"処理結果: {response.get('message', '')[:100]}...")
    
    if 'routing_decision' in response:
        routing_info = response['routing_decision']
        print(f"実際の処理エージェント: {routing_info['selected_agent']}")
        print(f"ルーティング信頼度: {routing_info['confidence']}")