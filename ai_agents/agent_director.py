from typing import List, Any, Dict, Optional
import json

from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph
from langgraph.constants import START, END

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.task_planner import SortedTaskExtractorAndRouterNode, TaskGrouper, TaskDistributor
from ai_agents.product_center.product_center_agent_manager import ProductCenterAgentManager


class AgentDirectorState(BaseAgentState):
    """
    AgentDirector専用の状態クラス - TaskPlanner情報を含む
    """
    sorted_routed_tasks: Optional[List[Dict[str, Any]]]  # ソート・ルーティング済みタスクリスト (Combined Step 1 & 2)
    grouped_tasks: Optional[Dict[str, List[Dict[str, Any]]]]  # グループ化されたタスク辞書 (Step 3)
    distributed_tasks: Optional[Dict[str, Any]]  # 配信されたタスク結果 (Step 4)
    task_planning_info: Optional[Dict[str, Any]]  # TaskPlanner情報


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
        # SortedTaskExtractorAndRouterNodeを初期化（Combined Step 1 & 2: 構造化意図抽出・ルーティング・ソート）
        self.sorted_task_extractor_router = SortedTaskExtractorAndRouterNode(self.llm_handler, self.langfuse_handler)
        # TaskGrouperを初期化（Step 3: タスクグループ化）
        self.task_grouper = TaskGrouper()

        # 下流AgentManagerを事前登録
        self.registered_agent_managers = {
            "product_center_agent_manager": ProductCenterAgentManager
        }

        # TaskDistributorを初期化（Step 4: タスク配信）
        self.task_distributor = TaskDistributor(
            self.llm_handler,
            registered_managers=self.registered_agent_managers
        )

    def _initialize_tools(self):
        """AgentDirector用ツールを初期化"""
        # AgentDirectorは直接ツールを使用せず、TaskPlannerと下流Agentに委譲
        return []

    def _get_state_class(self):
        """AgentDirector専用の状態クラスを返す"""
        return AgentDirectorState

    def _sorted_task_extractor_router_node(self, state: AgentDirectorState) -> AgentDirectorState:
        """
        SortedTaskExtractorAndRouter Node - ユーザー入力から構造化・ルーティング・ソート済みタスクを一括生成
        LangGraphワークフローの一部として実行される (Combined Step 1 & 2)
        """
        print(f"🎯🔀 SortedTaskExtractorAndRouter Node: 統合タスク処理を開始...")

        try:
            # ユーザー入力を取得
            user_input = state.get("user_input", "")
            if not user_input:
                # メッセージから入力を取得
                messages = state.get("messages", [])
                if messages:
                    user_input = messages[0].content

            print(f"📝 入力: {user_input}")

            # SortedTaskExtractorAndRouterNodeで統合処理
            sorted_routed_tasks = self.sorted_task_extractor_router.extract_route_and_sort_tasks(user_input, state.get("session_id", None), state.get("user_id", None))

            print(f"✅ 統合タスク処理完了: {len(sorted_routed_tasks)}個のタスクを抽出・ルーティング・ソート")
            for i, task in enumerate(sorted_routed_tasks, 1):
                priority = task.get("priority", "N/A")
                action = task.get("command", {}).get("action", "N/A")
                condition = task.get("command", {}).get("condition", "N/A")
                agent = task.get("target_agent", "N/A")
                print(f"  タスク{i}: 優先度{priority} - {action} ({condition}) -> {agent}")

            # 状態を更新
            state["sorted_routed_tasks"] = sorted_routed_tasks
            state["task_planning_info"] = {
                "step": "1&2_combined",
                "description": "Structured intent extraction, routing, and sorting completed in one step",
                "original_input": user_input,
                "sorted_routed_task_count": len(sorted_routed_tasks)
            }

            return state

        except Exception as e:
            print(f"❌ SortedTaskExtractorAndRouter Node エラー: {e}")
            # エラー時はフォールバックタスクを設定
            fallback_task = [{
                "target_agent": "product_center_agent_manager",
                "command": {
                    "action": "search_product",
                    "condition": f"user_request: {user_input}"
                },
                "priority": 1
            }]

            state["sorted_routed_tasks"] = fallback_task
            state["task_planning_info"] = {
                "step": "1&2_combined",
                "description": "Fallback task created due to extraction/routing error",
                "original_input": user_input,
                "sorted_routed_task_count": 1,
                "error": str(e)
            }

            return state

    def _task_grouper_node(self, state: AgentDirectorState) -> AgentDirectorState:
        """
        TaskGrouper Node - ソート・ルーティング済みタスクを同じtarget_agentごとにグループ化
        LangGraphワークフローの一部として実行される (Step 3)
        """
        print(f"🔗 TaskGrouper Node: タスクグループ化を開始...")

        try:
            # Combined Step 1&2の結果（ソート・ルーティングタスク）を取得
            sorted_routed_tasks = state.get("sorted_routed_tasks", [])
            if not sorted_routed_tasks:
                print("⚠️ ソート・ルーティングタスクが見つかりません。SortedTaskExtractorAndRouterNodeが正常に実行されていない可能性があります。")
                # フォールバックとして空のグループ化タスクを設定
                state["grouped_tasks"] = {}
                return state

            print(f"📝 入力: {len(sorted_routed_tasks)}個のソート・ルーティングタスク")

            # TaskGrouperでタスクグループ化（優先順位ソート済み）
            grouped_tasks = self.task_grouper.group_tasks(sorted_routed_tasks)

            print(f"✅ タスクグループ化完了: {len(grouped_tasks)}個のエージェントグループを作成")
            for agent, commands in grouped_tasks.items():
                print(f"  {agent}: {len(commands)}個のコマンド")

            # 状態を更新
            state["grouped_tasks"] = grouped_tasks

            # TaskPlanner情報を更新
            task_planning_info = state.get("task_planning_info", {})
            task_planning_info.update({
                "step": 3,
                "description": "Structured intent extraction, routing, sorting, and task grouping completed",
                "grouped_agent_count": len(grouped_tasks),
                "total_grouped_commands": sum(len(commands) for commands in grouped_tasks.values())
            })
            state["task_planning_info"] = task_planning_info

            return state

        except Exception as e:
            print(f"❌ TaskGrouper Node エラー: {e}")
            # エラー時はフォールバックグループ化を設定
            sorted_routed_tasks = state.get("sorted_routed_tasks", [])
            fallback_grouping = {}

            for task in sorted_routed_tasks:
                target_agent = task.get("target_agent", "unknown_agent")
                command = task.get("command", {"action": "fallback_action", "condition": "fallback_condition"})

                if target_agent not in fallback_grouping:
                    fallback_grouping[target_agent] = []
                fallback_grouping[target_agent].append(command)

            state["grouped_tasks"] = fallback_grouping

            # TaskPlanner情報を更新
            task_planning_info = state.get("task_planning_info", {})
            task_planning_info.update({
                "step": 3,
                "description": "Fallback task grouping created due to grouping error",
                "grouped_agent_count": len(fallback_grouping),
                "total_grouped_commands": sum(len(commands) for commands in fallback_grouping.values()),
                "error": str(e)
            })
            state["task_planning_info"] = task_planning_info

            return state

    def _task_distributor_node(self, state: AgentDirectorState) -> AgentDirectorState:
        """
        TaskDistributor Node - グループ化されたタスクを下流AgentManagerに配信
        LangGraphワークフローの一部として実行される (Step 4)
        """
        print(f"📤 TaskDistributor Node: タスク配信を開始...")

        try:
            # Step 3の結果（グループ化タスク）を取得
            grouped_tasks = state.get("grouped_tasks", {})
            if not grouped_tasks:
                print("⚠️ グループ化タスクが見つかりません。TaskGrouperが正常に実行されていない可能性があります。")
                # フォールバックとして空の配信結果を設定
                state["distributed_tasks"] = {
                    "distributed_tasks": {},
                    "execution_results": {},
                    "errors": ["グループ化タスクが見つかりません"],
                    "total_agents": 0,
                    "successful_distributions": 0,
                    "failed_distributions": 1
                }
                return state

            print(f"📝 入力: {len(grouped_tasks)}個のエージェントグループ")

            # ユーザーの元入力を取得
            original_user_input = state.get("user_input", "")
            if not original_user_input:
                # メッセージから入力を取得
                messages = state.get("messages", [])
                if messages:
                    original_user_input = messages[0].content

            # TaskDistributorでタスク配信・実行
            distribution_result = self.task_distributor.distribute_tasks(
                grouped_tasks,
                original_user_input,
                session_id=state.get("session_id", None),
                user_id=state.get("user_id", None),
            )

            print(f"✅ タスク配信完了: {distribution_result['successful_distributions']}個のエージェントに配信成功")
            if distribution_result['errors']:
                print(f"⚠️ 配信エラー: {len(distribution_result['errors'])}件")
                for error in distribution_result['errors']:
                    print(f"  - {error}")

            # 状態を更新
            state["distributed_tasks"] = distribution_result
            # TODO
            if "errors" in distribution_result and len(distribution_result["errors"]) > 0:
                print("❌ 配信結果にエラーがあります")
                errors = distribution_result["errors"]
                if isinstance(errors, (list, dict)):
                    errors = json.dumps(errors)
                elif errors is None:
                    errors = None
                else:
                    errors = str(errors)
                state["error_message"] = errors
            else:
                if "last_execution_result" in distribution_result:
                    print("✅ 配信結果にメッセージがあります")
                    state["messages"].append(AIMessage(content=distribution_result["last_execution_result"]["message"]))
                else:
                    print("⚠️ 配信結果にメッセージがありません")
                    state["error_message"] = "タスク配信が完了しましたが、結果はありません"

            # TaskPlanner情報を更新
            task_planning_info = state.get("task_planning_info", {})
            task_planning_info.update({
                "step": "1&2_combined+3+4",
                "description": "Structured intent extraction, routing, sorting, task grouping, and task distribution completed",
                "distributed_agent_count": distribution_result['successful_distributions'],
                "total_distribution_attempts": distribution_result['total_agents'],
                "distribution_errors": len(distribution_result['errors'])
            })
            state["task_planning_info"] = task_planning_info

            return state

        except Exception as e:
            print(f"❌ TaskDistributor Node エラー: {e}")
            # エラー時はフォールバック配信結果を設定
            fallback_distribution = {
                "distributed_tasks": {},
                "execution_results": {},
                "errors": [str(e)],
                "total_agents": 0,
                "successful_distributions": 0,
                "failed_distributions": 1
            }

            state["distributed_tasks"] = fallback_distribution

            # TaskPlanner情報を更新
            task_planning_info = state.get("task_planning_info", {})
            task_planning_info.update({
                "step": "1&2_combined+3+4",
                "description": "Fallback task distribution created due to distribution error",
                "distributed_agent_count": 0,
                "total_distribution_attempts": 0,
                "distribution_errors": 1,
                "error": str(e)
            })
            state["task_planning_info"] = task_planning_info

            return state

    def _build_workflow_graph(self):
        """
        AgentDirector専用ワークフローグラフを構築
        SortedTaskExtractorAndRouter -> TaskGrouper -> TaskDistributor -> Assistant -> Tools -> Assistant のフローを実装
        """
        # 状態グラフを定義
        state_class = self._get_state_class()
        builder = StateGraph(state_class)

        # ノードを追加
        builder.add_node("sorted_task_extractor_router", self._sorted_task_extractor_router_node)
        builder.add_node("task_grouper", self._task_grouper_node)
        builder.add_node("task_distributor", self._task_distributor_node)
        # builder.add_node("assistant", self._assistant_node)
        # builder.add_node("tools", self._custom_tool_node)

        # エッジを定義
        builder.add_edge(START, "sorted_task_extractor_router")
        builder.add_edge("sorted_task_extractor_router", "task_grouper")
        builder.add_edge("task_grouper", "task_distributor")
        builder.add_edge("task_distributor", END)
        # builder.add_conditional_edges(
        #     "assistant",
        #     tools_condition,
        # )
        # builder.add_edge("tools", "assistant")

        return builder.compile()

    def _process_final_state(self, final_state: AgentDirectorState) -> Dict[str, Any]:
        """
        AgentDirector専用の最終状態処理 - TaskPlanner情報を含む
        """
        # 基本的なレスポンスデータを取得
        response_data = super()._process_final_state(final_state)

        # TaskPlanner情報を追加
        if final_state.get("sorted_routed_tasks"):
            response_data["sorted_routed_tasks"] = final_state["sorted_routed_tasks"]

        if final_state.get("grouped_tasks"):
            response_data["grouped_tasks"] = final_state["grouped_tasks"]

        if final_state.get("distributed_tasks"):
            response_data["distributed_tasks"] = final_state["distributed_tasks"]

        if final_state.get("task_planning_info"):
            response_data["task_planning_info"] = final_state["task_planning_info"]

        return response_data

    def _get_system_message_content(self, is_entry_agent: bool = True) -> str:
        """Director system message with SortedTaskExtractorAndRouterNode integration"""
        return """
You are the AgentDirector, the supreme commander of a multi-layer Agent system.

## Your Purpose
    Execute the pre-planned, prioritized, and grouped tasks provided by the TaskPlanner workflow.

## Available AgentManager Tools
    - **product_center_agent_manager**: Handles product search, inventory management, price changes, product activation/deactivation

## Response Format
    - Structured JSON response
    - Include "html_content" field for direct screen rendering when needed
    - Include "error" field for error messages in Japanese
    - Include "next_actions" field for suggested next steps (considering conversation history)

## Important Principles
    1. **Error handling**: Handle execution errors gracefully and provide meaningful feedback
    2. **Context preservation**: Maintain conversation history and execution context

## Conversation History Usage
    - **Continuity**: Remember previous operations and search results for informed execution
    - **Progress tracking**: Build upon previous execution results and maintain workflow state
    - **Error correction**: Learn from past execution errors to improve current execution
    - **Information reuse**: Leverage previously obtained data to optimize current execution

Always respond in friendly, clear Japanese while executing tasks efficiently and providing meaningful progress updates.
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
