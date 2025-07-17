from typing import List, Any, Dict, Optional
import json

from langchain_core.messages import AIMessage
from langchain.schema import HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.constants import START, END

from ai_agents.base_agent import BaseAgent, BaseAgentState
from ai_agents.intelligent_agent_router import AgentCapability
from ai_agents.task_planner import AgentManagerRegistry, SortedTaskExtractorAndRouterNode, TaskGrouper, TaskDistributor
from ai_agents.product_center.product_center_agent_manager import ProductCenterAgentManager
from ai_agents.order_center.order_center_agent_manager import OrderCenterAgentManager


class AgentDirectorState(BaseAgentState):
    """
    AgentDirector専用の状態クラス - TaskPlanner情報を含む
    """
    sorted_routed_tasks: Optional[List[Dict[str, Any]]]  # ソート・ルーティング済みタスクリスト (Combined Step 1 & 2)
    grouped_tasks: Optional[Dict[str, List[Dict[str, Any]]]]  # グループ化されたタスク辞書 (Step 3)
    distributed_tasks: Optional[Dict[str, Any]]  # 配信されたタスク結果 (Step 4)
    task_planning_info: Optional[Dict[str, Any]]  # TaskPlanner情報
    completion_retry_count: Optional[int]  # タスク完了チェックの再試行回数
    task_completion_status: Optional[str]  # タスク完了状態 ("completed", "incomplete", "failed")
    incomplete_tasks: Optional[Dict[str, List[Dict[str, Any]]]]  # 未完了タスク（再実行用）


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

        # 下流AgentManagerを事前登録
        registered_agent_managers = {
            "ProductCenterAgentManager": ProductCenterAgentManager,
            "OrderCenterAgentManager": OrderCenterAgentManager
        }

        # AgentManagerRegistryを初期化（共有インスタンス管理）
        self.agent_manager_registry = AgentManagerRegistry(
            self.llm_handler,
            registered_managers=registered_agent_managers
        )

        # SortedTaskExtractorAndRouterNodeを初期化（Combined Step 1 & 2: 構造化意図抽出・ルーティング・ソート）
        self.sorted_task_extractor_router = SortedTaskExtractorAndRouterNode(
            self.llm_handler, 
            self.langfuse_handler,
            agent_manager_registry=self.agent_manager_registry
        )
        # TaskGrouperを初期化（Step 3: タスクグループ化）
        self.task_grouper = TaskGrouper()

        # TaskDistributorを初期化（Step 4: タスク配信）
        self.task_distributor = TaskDistributor(
            self.llm_handler,
            agent_manager_registry=self.agent_manager_registry
        )

    def _initialize_tools(self):
        """AgentDirector用ツールを初期化"""
        # AgentDirectorは直接ツールを使用せず、TaskPlannerと下流Agentに委譲
        return []

    def get_state_class(self):
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
            user_input = state.get("user_input", "")
            if not user_input:
                messages = state.get("messages", [])
                if messages:
                    user_input = messages[0].content

            fallback_task = [{
                "target_agent": "ProductCenterAgentManager",
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
            # AgentDirectorの現在の状態を初期共有状態として渡す
            distribution_result = self.task_distributor.distribute_tasks(
                grouped_tasks,
                original_user_input,
                session_id=state.get("session_id", None),
                user_id=state.get("user_id", None),
                initial_shared_state=state  # AgentDirectorの状態を渡す
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

    def _summarize_task_execution_with_llm(self, state: AgentDirectorState, is_completed: bool) -> str:
        """
        LLMを使用してタスク実行状況を要約する

        Args:
            state: AgentDirectorState
            is_completed: 全タスクが完了したかどうか

        Returns:
            LLMによる要約メッセージ
        """
        try:
            # ユーザーの元の要求を取得
            original_user_input = state.get("user_input", "")
            if not original_user_input:
                messages = state.get("messages", [])
                if messages:
                    original_user_input = messages[0].content

            distributed_tasks = state.get("distributed_tasks", {})
            execution_results = distributed_tasks.get("execution_results", {})
            errors = distributed_tasks.get("errors", [])
            retry_count = state.get("completion_retry_count", 0)

            # タスク実行情報を整理
            task_summary = {
                "original_request": original_user_input,
                "total_agents": distributed_tasks.get("total_agents", 0),
                "successful_distributions": distributed_tasks.get("successful_distributions", 0),
                "failed_distributions": distributed_tasks.get("failed_distributions", 0),
                "retry_count": retry_count,
                "is_completed": is_completed,
                "execution_results": {},
                "errors": errors[:3]  # 最大3つのエラーを含める
            }

            # 実行結果を整理
            for agent, result in execution_results.items():
                if isinstance(result, dict):
                    task_summary["execution_results"][agent] = {
                        "message": result.get("message", "実行完了"),
                        "status": "success" if result.get("message") else "completed"
                    }
                else:
                    task_summary["execution_results"][agent] = {
                        "message": str(result),
                        "status": "completed"
                    }

            # Create LLM prompts in English
            if is_completed:
                system_prompt = """You are an excellent task execution result summarizer.
Please summarize the results of tasks executed in response to user requests in a clear and concise manner.

When summarizing, please pay attention to the following points:
1. Clearly indicate the user's original request
2. Specifically describe the results of executed tasks
3. Emphasize successful content
4. Avoid technical terms and explain in general language
5. If there are multiple results, organize them in order of importance
6. Use a positive and constructive tone

## Response Format
    - Structured JSON response
    - MUST Include "html_content" field for direct screen rendering when needed
    - Include "error" field for error messages in Japanese
    - Include "next_actions" field for suggested next steps (considering conversation history)
        * Type: string (single action) OR array of strings (multiple actions)

Please provide a comprehensive summary that follows the structured response format above."""
            else:
                system_prompt = """You are an excellent task execution result summarizer.
Please summarize the results of tasks executed in response to user requests, including any issues, in an understandable manner.

When summarizing, please pay attention to the following points:
1. Clearly indicate the user's original request
2. Clearly separate successful tasks from failed tasks
3. Explain the causes of failures as much as possible
4. If there are successful parts, evaluate them appropriately
5. Avoid technical terms and explain in general language
6. Use a constructive and solution-oriented tone
7. Appropriately mention the number of retry attempts

## Response Format
    - Structured JSON response
    - MUST Include "html_content" field for direct screen rendering when needed
    - Include "error" field for error messages in Japanese
    - Include "next_actions" field for suggested next steps (considering conversation history)
        * Type: string (single action) OR array of strings (multiple actions)

Please provide a comprehensive summary that follows the structured response format above, focusing on both successes and areas that need attention."""

            user_prompt = f"""Please summarize the following task execution information:

【User Request】
{task_summary['original_request']}

【Execution Status】
- Total agents: {task_summary['total_agents']}
- Successful tasks: {task_summary['successful_distributions']}
- Failed tasks: {task_summary['failed_distributions']}
- Retry count: {task_summary['retry_count']}
- Completion status: {'All completed' if is_completed else 'Partially incomplete'}

【Execution Results】"""

            for agent, result in task_summary['execution_results'].items():
                user_prompt += f"\n- {agent}: {result['message']}"

            if task_summary['errors']:
                user_prompt += f"\n\n【Error Information】"
                for i, error in enumerate(task_summary['errors'], 1):
                    user_prompt += f"\n{i}. {error}"

            user_prompt += "\n\nBased on the above information, please create a comprehensive summary that is easy for users to understand. Remember to follow the structured JSON response format with html_content, error, and next_actions fields as specified."

            # LLMに要約を依頼
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            print(f"🤖 LLMによるタスク実行結果の要約を生成中...")
            response = self.llm_handler.get_llm().invoke(messages)

            if hasattr(response, 'content'):
                summary = response.content
                # JSONブロックを探す（```json...```の形式も対応）
                if "```json" in summary:
                    start = summary.find("```json") + 7
                    end = summary.find("```", start)
                    json_summary = summary[start:end].strip()
                elif "```" in summary:
                    start = summary.find("```") + 3
                    end = summary.find("```", start)
                    json_summary = summary[start:end].strip()
                else:
                    json_summary = summary

                print(f"✅ LLM要約完了: {len(json_summary)}文字")
                print(f"📝 LLM要約内容プレビュー: {json_summary[:100]}...")
                return json_summary
            else:
                summary = str(response)
                print(f"✅ LLM要約完了 (文字列変換): {len(summary)}文字")
                print(f"📝 LLM要約内容プレビュー: {summary[:100]}...")
                return summary

        except Exception as e:
            print(f"❌ LLM要約エラー: {e}")
            import traceback
            traceback.print_exc()
            # フォールバック: 従来の方式で要約を作成
            retry_count = state.get("completion_retry_count", 0)
            if is_completed:
                return "✅ 全てのタスクが正常に完了しました。"
            else:
                return f"⚠️ 一部のタスクが完了しませんでした（{retry_count}回再試行後）。"

    def _task_completion_checker_node(self, state: AgentDirectorState) -> AgentDirectorState:
        """
        TaskCompletionChecker Node - タスク完了状況をチェックし、必要に応じて再実行
        未完了タスクがある場合は最大3回まで再試行する
        """
        print(f"🔍 TaskCompletionChecker Node: タスク完了状況をチェック中...")

        try:
            # 初期化
            if state.get("completion_retry_count") is None:
                state["completion_retry_count"] = 0

            retry_count = state.get("completion_retry_count", 0)
            distributed_tasks = state.get("distributed_tasks", {})

            if not distributed_tasks:
                print("⚠️ 配信されたタスクが見つかりません")
                state["task_completion_status"] = "failed"
                state["error_message"] = "配信されたタスクが見つかりません"
                return state

            # タスク完了状況を分析
            total_agents = distributed_tasks.get("total_agents", 0)
            successful_distributions = distributed_tasks.get("successful_distributions", 0)
            errors = distributed_tasks.get("errors", [])
            execution_results = distributed_tasks.get("execution_results", {})

            print(f"📊 タスク実行状況: {successful_distributions}/{total_agents} 成功, エラー数: {len(errors)}")

            # 全タスクが成功した場合
            if successful_distributions == total_agents and len(errors) == 0:
                print("✅ 全てのタスクが正常に完了しました")
                state["task_completion_status"] = "completed"

                # LLMを使用して最終結果を要約
                final_message = self._summarize_task_execution_with_llm(state, is_completed=True)
                state["messages"].append(AIMessage(content=final_message))
                return state

            # 一部のタスクが失敗した場合
            print(f"⚠️ 一部のタスクが未完了です (再試行回数: {retry_count}/3)")

            # 最大再試行回数に達した場合
            if retry_count >= 3:
                print("❌ 最大再試行回数に達しました。最終結果を報告します")
                state["task_completion_status"] = "failed"

                # LLMを使用して最終結果を要約
                final_message = self._summarize_task_execution_with_llm(state, is_completed=False)
                state["messages"].append(AIMessage(content=final_message))
                return state

            # 再試行を実行
            print(f"🔄 未完了タスクの再実行を開始します (試行 {retry_count + 1}/3)")

            # 失敗したタスクを特定して再グループ化
            incomplete_tasks = self._identify_incomplete_tasks(state)

            if incomplete_tasks:
                print(f"📝 再実行対象: {len(incomplete_tasks)}個のエージェントグループ")

                # 再試行カウントを増加
                state["completion_retry_count"] = retry_count + 1
                state["incomplete_tasks"] = incomplete_tasks

                # 未完了タスクを再配信
                original_user_input = state.get("user_input", "")
                if not original_user_input:
                    messages = state.get("messages", [])
                    if messages:
                        original_user_input = messages[0].content

                retry_distribution_result = self.task_distributor.distribute_tasks(
                    incomplete_tasks,
                    original_user_input,
                    session_id=state.get("session_id", None),
                    user_id=state.get("user_id", None),
                    initial_shared_state=state
                )

                # 結果をマージ
                self._merge_distribution_results(state, retry_distribution_result)

                # 再帰的に完了チェックを実行
                return self._task_completion_checker_node(state)
            else:
                print("⚠️ 再実行対象のタスクが特定できませんでした")
                state["task_completion_status"] = "failed"
                state["error_message"] = "再実行対象のタスクが特定できませんでした"
                return state

        except Exception as e:
            print(f"❌ TaskCompletionChecker Node エラー: {e}")
            state["task_completion_status"] = "failed"
            state["error_message"] = f"タスク完了チェック中にエラーが発生しました: {str(e)}"
            return state

    def _identify_incomplete_tasks(self, state: AgentDirectorState) -> Dict[str, List[Dict[str, Any]]]:
        """
        未完了タスクを特定して再実行用のタスクグループを作成
        """
        try:
            distributed_tasks = state.get("distributed_tasks", {})
            grouped_tasks = state.get("grouped_tasks", {})

            distributed_task_info = distributed_tasks.get("distributed_tasks", {})
            errors = distributed_tasks.get("errors", [])

            incomplete_tasks = {}

            # エラーが発生したエージェントを特定
            for agent_name, task_group in grouped_tasks.items():
                # 配信されたタスクに含まれていない、または実行に失敗したエージェント
                if agent_name not in distributed_task_info or distributed_task_info[agent_name].get("status") != "executed":
                    incomplete_tasks[agent_name] = task_group
                    print(f"🔄 再実行対象に追加: {agent_name}")

            return incomplete_tasks

        except Exception as e:
            print(f"❌ 未完了タスク特定エラー: {e}")
            return {}

    def _merge_distribution_results(self, state: AgentDirectorState, retry_result: Dict[str, Any]):
        """
        再試行結果を既存の配信結果にマージ
        """
        try:
            original_distributed = state.get("distributed_tasks", {})

            # 配信されたタスクをマージ
            original_distributed_tasks = original_distributed.get("distributed_tasks", {})
            retry_distributed_tasks = retry_result.get("distributed_tasks", {})
            original_distributed_tasks.update(retry_distributed_tasks)

            # 実行結果をマージ
            original_execution_results = original_distributed.get("execution_results", {})
            retry_execution_results = retry_result.get("execution_results", {})
            original_execution_results.update(retry_execution_results)

            # エラーをマージ
            original_errors = original_distributed.get("errors", [])
            retry_errors = retry_result.get("errors", [])
            merged_errors = original_errors + retry_errors

            # カウンターを更新
            original_successful = original_distributed.get("successful_distributions", 0)
            retry_successful = retry_result.get("successful_distributions", 0)

            original_failed = original_distributed.get("failed_distributions", 0)
            retry_failed = retry_result.get("failed_distributions", 0)

            # 最終結果を更新
            if retry_result.get("last_execution_result"):
                original_distributed["last_execution_result"] = retry_result["last_execution_result"]

            # マージされた結果で更新
            state["distributed_tasks"] = {
                "distributed_tasks": original_distributed_tasks,
                "execution_results": original_execution_results,
                "errors": merged_errors,
                "total_agents": original_distributed.get("total_agents", 0),
                "successful_distributions": len(original_distributed_tasks),
                "failed_distributions": len(merged_errors),
                "last_execution_result": original_distributed.get("last_execution_result", {})
            }

            print(f"🔄 結果マージ完了: 成功 {len(original_distributed_tasks)}, エラー {len(merged_errors)}")

        except Exception as e:
            print(f"❌ 結果マージエラー: {e}")

    def _build_workflow_graph(self):
        """
        AgentDirector専用ワークフローグラフを構築
        SortedTaskExtractorAndRouter -> TaskGrouper -> TaskDistributor -> TaskCompletionChecker -> END のフローを実装
        """
        # 状態グラフを定義
        state_class = self.get_state_class()
        builder = StateGraph(state_class)

        # ノードを追加
        builder.add_node("sorted_task_extractor_router", self._sorted_task_extractor_router_node)
        builder.add_node("task_grouper", self._task_grouper_node)
        builder.add_node("task_distributor", self._task_distributor_node)
        builder.add_node("task_completion_checker", self._task_completion_checker_node)
        # builder.add_node("assistant", self._assistant_node)
        # builder.add_node("tools", self._custom_tool_node)

        # エッジを定義
        builder.add_edge(START, "sorted_task_extractor_router")
        builder.add_edge("sorted_task_extractor_router", "task_grouper")
        builder.add_edge("task_grouper", "task_distributor")
        builder.add_edge("task_distributor", "task_completion_checker")
        builder.add_edge("task_completion_checker", END)
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

        # タスク完了チェック情報を追加
        if final_state.get("completion_retry_count") is not None:
            response_data["completion_retry_count"] = final_state["completion_retry_count"]

        if final_state.get("task_completion_status"):
            response_data["task_completion_status"] = final_state["task_completion_status"]

        if final_state.get("incomplete_tasks"):
            response_data["incomplete_tasks"] = final_state["incomplete_tasks"]

        return response_data

    def _get_system_message_content(self, is_entry_agent: bool = True) -> str:
        """Director system message with SortedTaskExtractorAndRouterNode integration"""
        pass

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

if __name__ == "__main__":
    # AgentDirectorのインスタンスを作成
    import os
    from dotenv import load_dotenv

    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    director = AgentDirector(api_key=api_key, llm_type="ollama_qwen3")

    response = director.process_command(
        "Jancode 1000000000001の商品を検索してください",
        llm_type="ollama_qwen3",
        session_id="session_1751867378920_795rpr9um",
        user_id="default_user",
        is_entry_agent=True,
    )
