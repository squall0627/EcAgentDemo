from typing import List, Dict, Any
import json
from llm.llm_handler import LLMHandler
from langchain.schema import HumanMessage, SystemMessage

from utils.langfuse_handler import LangfuseHandler
from utils.string_utils import clean_think_output


class SortedTaskExtractorAndRouterNode:
    """
    統合タスク抽出・ルーティング・ソートノード
    ユーザーの自然言語入力から構造化されたタスクリストを抽出し、
    適切なAgentManagerにルーティングし、実行優先順位を付与する
    Step 1: Extract structured intent, route to agents, and sort by priority
    """

    def __init__(self, llm_handler: LLMHandler, langfuse_handler: LangfuseHandler):
        """
        SortedTaskExtractorAndRouterNode初期化

        Args:
            llm_handler: LLMHandlerインスタンス
            langfuse_handler: LangfuseHandlerインスタンス
        """
        self.llm_handler = llm_handler
        self.langfuse_handler = langfuse_handler

    def _get_combined_prompt(self) -> str:
        """統合タスク抽出・ルーティング・ソート用のプロンプトを取得"""
        return """
You are a high-performance task decomposition, routing, and prioritization system for an e-commerce management system.

# Input: User's natural language request
# Output: Structured, routed, and prioritized task list

## Your Purpose
    1. Extract clear, actionable tasks from user input
    2. Use precise conditions that can be programmatically evaluated
    3. Route each task to the appropriate downstream AgentManager
    4. Assign execution priority based on business logic and dependencies
    5. Output tasks in a format ready for downstream execution
    6. Support multiple languages (Japanese, English, etc.)

## Output Format (JSON):
[
  {
    "target_agent": "agent_manager_name",
    "command": {
      "action": "action_name",
      "condition": "condition_description"
    },
    "priority": 1
  }
]

## Available Target Agents:
- product_center_agent_manager: Handles all product-related operations

## Priority Assignment Rules:
1. **Dependency-based Priority**: If one task depends on another, assign higher priority to the prerequisite
   - Example: search_product (priority 1) → update_inventory (priority 2) for the found products

## Rules:
1. If input is ambiguous, create the most reasonable interpretation

## Examples:

Input: "在庫がない商品を棚下げして、価格が5000円以上のものは値下げしてください。"
Output:
[
  {
    "target_agent": "product_center_agent_manager",
    "command": {
      "action": "deactivate_product",
      "condition": "在庫なし"
    },
    "priority": 1
  },
  {
    "target_agent": "product_center_agent_manager",
    "command": {
      "action": "discount_product",
      "condition": "価格 > 5000"
    },
    "priority": 2
  }
]

Input: "Search for coffee products and update their inventory"
Output:
[
  {
    "target_agent": "product_center_agent_manager",
    "command": {
      "action": "search_product",
      "condition": "product_name contains 'coffee'"
    },
    "priority": 1
  },
  {
    "target_agent": "product_center_agent_manager",
    "command": {
      "action": "update_inventory",
      "condition": "product_name contains 'coffee'"
    },
    "priority": 2
  }
]

Now extract, route, and prioritize tasks from the following user input:
"""

    def extract_route_and_sort_tasks(self, user_input: str, session_id: str = None, user_id: str = None) -> List[Dict[str, Any]]:
        """
        ユーザー入力から構造化されたタスクを抽出し、ルーティングし、優先順位を付与

        Args:
            user_input: ユーザーの自然言語入力
            session_id: セッションID（オプション）
            user_id: ユーザーID（オプション）

        Returns:
            構造化・ルーティング・ソート済みタスクリスト
        """
        try:
            # システムメッセージとユーザー入力を組み合わせ
            messages = [
                SystemMessage(content=self._get_combined_prompt()),
                HumanMessage(content=user_input)
            ]

            # LLMに送信して構造化・ルーティング・ソート済みタスクを取得
            llm = self.llm_handler.get_llm()
            config = self.langfuse_handler.get_config("SortedTaskExtractorAndRouter", session_id, user_id)
            response = llm.invoke(messages, config=config)

            # レスポンスからJSONを抽出
            response_content = response.content.strip()
            response_content, thoughts = clean_think_output(response_content)
            if thoughts:
                print("\n🤔 LLM Thoughts:")
                print(thoughts)

            # JSONブロックを探す（```json...```の形式も対応）
            # Display LLM thoughts before parsing JSON
            if "```json" in response_content:
                start = response_content.find("```json") + 7
                end = response_content.find("```", start)
                json_content = response_content[start:end].strip()
            elif "```" in response_content:
                start = response_content.find("```") + 3
                end = response_content.find("```", start)
                json_content = response_content[start:end].strip()
            else:
                json_content = response_content

            # JSONをパース
            sorted_routed_tasks = json.loads(json_content)

            # 結果を検証
            if not isinstance(sorted_routed_tasks, list):
                raise ValueError("Expected list of tasks")

            # 各タスクの必須フィールドを検証
            for task in sorted_routed_tasks:
                required_fields = ["target_agent", "command", "priority"]
                for field in required_fields:
                    if field not in task:
                        raise ValueError(f"Missing required field: {field}")

                # commandの必須フィールドを検証
                command = task.get("command", {})
                if not isinstance(command, dict):
                    raise ValueError("Command must be a dictionary")

                command_required_fields = ["action", "condition"]
                for field in command_required_fields:
                    if field not in command:
                        raise ValueError(f"Missing required command field: {field}")

                # priorityが数値であることを確認
                if not isinstance(task.get("priority"), int):
                    raise ValueError("Priority must be an integer")

            return sorted_routed_tasks

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析エラー: {e}")
            print(f"レスポンス内容: {response_content}")
            # フォールバック: 基本的なタスクを返す
            return self._create_fallback_task(user_input)
        except Exception as e:
            print(f"❌ 統合タスク処理エラー: {e}")
            return self._create_fallback_task(user_input)

    def _create_fallback_task(self, user_input: str) -> List[Dict[str, Any]]:
        """
        エラー時のフォールバックタスクを作成

        Args:
            user_input: ユーザー入力

        Returns:
            基本的なタスクリスト
        """
        # TODO
        return [
            {
                "target_agent": "product_center_agent_manager",
                "command": {
                    "action": "search_product",
                    "condition": f"user_request: {user_input}"
                },
                "priority": 1
            }
        ]

class TaskGrouper:
    """
    タスクグループ化器 - 同じ下流AgentManagerを使用する隣接タスクを合併
    Step 2: Task Grouping (同類タスクの集約)
    """

    def __init__(self):
        """
        TaskGrouper初期化
        LLMを使用せず、純粋なロジックでタスクをグループ化
        """
        pass

    def group_tasks(self, routed_tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        ルーティングされたタスクを優先順位でソートしてから同じtarget_agentごとにグループ化
        優先順位順に並べた後、隣接する同じtarget_agentのタスクのみを合併（非隣接は合併しない）

        Args:
            routed_tasks: SortedTaskExtractorAndRouterNodeで生成されたルーティング・ソート済みタスクリスト

        Returns:
            グループ化されたタスク辞書 {target_agent: [commands]}
        """
        try:
            # 入力検証
            if not routed_tasks or not isinstance(routed_tasks, list):
                print("⚠️ 無効なルーティングタスクリスト")
                return {}

            print(f"🔗 TaskGrouper: {len(routed_tasks)}個のタスクをグループ化中...")

            # Step 1: 優先順位でタスクをソート
            sorted_tasks = sorted(routed_tasks, key=lambda x: x.get("priority", 999))

            print(f"📊 優先順位ソート完了:")
            for i, task in enumerate(sorted_tasks, 1):
                priority = task.get("priority", "N/A")
                action = task.get("command", {}).get("action", "N/A")
                agent = task.get("target_agent", "N/A")
                print(f"  {i}. 優先度{priority}: {action} -> {agent}")

            # Step 2: ソート済みタスクを隣接する同じtarget_agentごとにグループ化
            grouped_tasks = {}
            current_agent = None
            current_group = []

            for i, task in enumerate(sorted_tasks):
                target_agent = task.get("target_agent")
                command = task.get("command", {})

                if not target_agent or not command:
                    print(f"⚠️ タスク{i+1}: 無効な形式をスキップ")
                    continue

                # 新しいエージェントまたは非隣接の場合
                if target_agent != current_agent:
                    # 前のグループを保存
                    if current_agent and current_group:
                        if current_agent not in grouped_tasks:
                            grouped_tasks[current_agent] = []
                        grouped_tasks[current_agent].extend(current_group)

                    # 新しいグループを開始
                    current_agent = target_agent
                    current_group = [command]
                else:
                    # 同じエージェントの隣接タスクを追加
                    current_group.append(command)

            # 最後のグループを保存
            if current_agent and current_group:
                if current_agent not in grouped_tasks:
                    grouped_tasks[current_agent] = []
                grouped_tasks[current_agent].extend(current_group)

            print(f"✅ タスクグループ化完了: {len(grouped_tasks)}個のエージェントグループを作成")
            for agent, commands in grouped_tasks.items():
                print(f"  {agent}: {len(commands)}個のコマンド")
                for j, cmd in enumerate(commands, 1):
                    print(f"    コマンド{j}: {cmd.get('action', 'N/A')} - {cmd.get('condition', 'N/A')}")

            return grouped_tasks

        except Exception as e:
            print(f"❌ タスクグループ化エラー: {e}")
            return self._create_fallback_grouping(routed_tasks)

    def _create_fallback_grouping(self, routed_tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        エラー時のフォールバックグループ化を作成

        Args:
            routed_tasks: 元のルーティングタスクリスト

        Returns:
            基本的なグループ化辞書
        """
        # TODO
        fallback_grouping = {}

        for task in routed_tasks:
            target_agent = task.get("target_agent", "unknown_agent")
            command = task.get("command", {"action": "fallback_action", "condition": "fallback_condition"})

            if target_agent not in fallback_grouping:
                fallback_grouping[target_agent] = []
            fallback_grouping[target_agent].append(command)

        return fallback_grouping


class TaskDistributor:
    """
    タスク配信器 - グループ化されたタスクを下流AgentManagerに配信・実行
    Step 3: 逐層下発任務到下游 AgentManager (Task Distribution and Execution)
    """

    def __init__(self, llm_handler: LLMHandler, registered_managers: Dict[str, Any] = None):
        """
        TaskDistributor初期化

        Args:
            llm_handler: LLMHandlerインスタンス
            registered_managers: 登録済みAgentManagerクラス辞書
        """
        self.llm_handler = llm_handler
        self.registered_managers = registered_managers or {}
        self.agent_manager_instances = {}  # 作成済みインスタンスのキャッシュ

    def distribute_tasks(self, grouped_tasks: Dict[str, List[Dict[str, Any]]], original_user_input: str = "", session_id: str = None, user_id: str = None, initial_shared_state=None) -> Dict[str, Any]:
        """
        グループ化されたタスクを下流AgentManagerに配信・実行

        Args:
            grouped_tasks: グループ化されたタスク辞書 {target_agent: [commands]}
            original_user_input: ユーザーの元入力
            session_id: セッションID（オプション）
            user_id: ユーザーID（オプション）
            initial_shared_state: AgentDirectorから渡された初期共有状態（BaseAgentState）

        Returns:
            配信・実行結果辞書
        """
        try:
            # 入力検証
            if not grouped_tasks or not isinstance(grouped_tasks, dict):
                print("⚠️ 無効なグループ化タスク辞書")
                return {"distributed_tasks": {}, "execution_results": {}, "errors": []}

            print(f"📤 TaskDistributor: {len(grouped_tasks)}個のエージェントグループにタスクを配信・実行中...")

            distributed_tasks = {}
            execution_results = {}
            errors = []
            previous_results = {}  # 前のタスクの結果を保存
            last_execution_result = {}  # 最後の実行結果を保存

            # 各エージェントグループに対してタスクを順次実行
            # AgentDirectorから渡された初期共有状態を使用、なければNoneで初期化
            shared_state = initial_shared_state  # AgentDirectorから渡された共有状態を利用

            for target_agent, commands in grouped_tasks.items():
                print(f"🎯 {target_agent}に{len(commands)}個のコマンドを実行中...")

                try:
                    # AgentManagerインスタンスを取得または作成
                    agent_manager = self._get_or_create_agent_manager(target_agent)

                    if not agent_manager:
                        error_msg = f"AgentManagerが見つかりません: {target_agent}"
                        print(f"❌ {error_msg}")
                        errors.append(error_msg)
                        continue

                    # 複数のコマンドを統合した指示を作成
                    integrated_command = self._integrate_commands(commands, previous_results)

                    print(f"📋 統合コマンド: {integrated_command}")

                    # AgentManagerのprocess_commandを実行
                    result = agent_manager.process_command(
                        command=integrated_command,
                        user_input=original_user_input,
                        llm_type=self.llm_handler.llm_type,
                        session_id=session_id,
                        user_id=user_id,
                        is_entry_agent=False,
                        shared_state=shared_state
                    )

                    # 結果を解析（BaseAgentStateオブジェクトまたはJSON文字列の場合の処理）
                    if isinstance(result, str):
                        # 従来のJSON文字列レスポンス（後方互換性）
                        try:
                            result = json.loads(result)
                        except json.JSONDecodeError:
                            result = {"message": result, "raw_response": True}
                    elif isinstance(result, dict):
                        # BaseAgentStateオブジェクトの場合、そのまま使用
                        # 必要に応じて後方互換性のためのフィールドを追加
                        if "message" not in result and result.get("response_message"):
                            result["message"] = result["response_message"]
                        elif "message" not in result and result.get("messages"):
                            # messagesから最後のメッセージを取得
                            last_message = result["messages"][-1] if result["messages"] else None
                            if last_message and hasattr(last_message, 'content'):
                                result["message"] = last_message.content
                            else:
                                result["message"] = "処理が完了しました"

                    print(f"✅ {target_agent}の実行完了")

                    # 配信・実行記録
                    distributed_tasks[target_agent] = {
                        "commands": commands,
                        "integrated_command": integrated_command,
                        "agent_manager_class": agent_manager.__class__.__name__,
                        "status": "executed"
                    }

                    # 実行結果を保存
                    execution_results[target_agent] = result

                    # 次のタスクのために結果を保存
                    previous_results[target_agent] = result

                    # 最後の実行結果を更新
                    last_execution_result = result

                    # 共有状態を更新（次のAgentで使用）
                    if isinstance(result, dict) and "messages" in result:
                        # BaseAgentStateオブジェクトの場合、そのまま共有状態として使用
                        shared_state = result
                        print(f"✅ {target_agent}の実行結果を共有状態として保存")

                except Exception as e:
                    error_msg = f"{target_agent}の実行エラー: {str(e)}"
                    print(f"❌ {error_msg}")
                    errors.append(error_msg)

            print(f"✅ タスク配信・実行完了: {len(distributed_tasks)}個のエージェントを実行")

            return {
                "distributed_tasks": distributed_tasks,
                "execution_results": execution_results,
                "errors": errors,
                "total_agents": len(grouped_tasks),
                "successful_distributions": len(distributed_tasks),
                "failed_distributions": len(errors),
                "previous_results": previous_results,
                "last_execution_result": last_execution_result
            }

        except Exception as e:
            print(f"❌ タスク配信・実行エラー: {e}")
            return {
                "distributed_tasks": {},
                "execution_results": {},
                "errors": [str(e)],
                "total_agents": 0,
                "successful_distributions": 0,
                "failed_distributions": 1,
            }

    def _get_or_create_agent_manager(self, target_agent: str):
        """
        対象エージェントのAgentManagerインスタンスを取得または作成

        Args:
            target_agent: 対象エージェント名

        Returns:
            AgentManagerインスタンス、見つからない場合はNone
        """
        # キャッシュから取得を試行
        if target_agent in self.agent_manager_instances:
            return self.agent_manager_instances[target_agent]

        # 登録済みマネージャーから作成
        if target_agent in self.registered_managers:
            manager_class = self.registered_managers[target_agent]
            try:
                # AgentManagerインスタンスを作成
                manager_instance = manager_class(
                    api_key=self.llm_handler.api_key,
                    llm_type=self.llm_handler.llm_type,
                    use_langfuse=True
                )

                # キャッシュに保存
                self.agent_manager_instances[target_agent] = manager_instance
                print(f"✅ {target_agent}のインスタンスを作成しました")

                return manager_instance

            except Exception as e:
                print(f"❌ {target_agent}のインスタンス作成エラー: {e}")
                return None

        print(f"⚠️ 登録されていないAgentManager: {target_agent}")
        return None

    def _integrate_commands(self, commands: List[Dict[str, Any]], previous_results: Dict[str, Any] = None) -> str:
        """
        複数のコマンドを統合した指示を作成（前のタスク結果を含む）

        Args:
            commands: コマンドリスト
            previous_results: 前のタスクの実行結果

        Returns:
            統合された指示文字列
        """
        if not commands:
            return "タスクがありません"

        # 前のタスク結果の要約を作成
        context_info = ""
        if previous_results:
            context_parts = []
            for agent, result in previous_results.items():
                if isinstance(result, dict):
                    message = result.get('message', '実行完了')
                    context_parts.append(f"- {agent}: {message}")
                else:
                    context_parts.append(f"- {agent}: {str(result)}")

            if context_parts:
                context_info = "前のタスクの実行結果:\n" + "\n".join(context_parts) + "\n\n"

        if len(commands) == 1:
            cmd = commands[0]
            action = cmd.get('action', 'unknown_action')
            condition = cmd.get('condition', 'unknown_condition')

            command_text = f"{action}: {condition}"
            if context_info:
                command_text = context_info + "上記の結果を踏まえて、以下のタスクを実行してください:\n" + command_text

            return command_text

        # 複数コマンドの場合は統合
        integrated_parts = []
        for i, cmd in enumerate(commands, 1):
            action = cmd.get('action', 'unknown_action')
            condition = cmd.get('condition', 'unknown_condition')
            integrated_parts.append(f"{i}. {action}: {condition}")

        command_text = "以下のタスクを順次実行してください:\n" + "\n".join(integrated_parts)

        if context_info:
            command_text = context_info + "上記の結果を踏まえて、" + command_text

        return command_text


class TaskPlanner:
    """
    タスクプランナー - 多層Agent系統のタスク計画を管理
    新アーキテクチャ: SortedTaskExtractorAndRouterNode + TaskGrouper + TaskDistributor
    Combined Step 1&2: 構造化意図抽出・ルーティング・ソート
    Step 3: タスクグループ化
    Step 4: タスク配信
    """

    def __init__(self, llm_handler: LLMHandler, langfuse_handler: LangfuseHandler = None):
        """
        TaskPlanner初期化

        Args:
            llm_handler: LLMHandlerインスタンス
            langfuse_handler: LangfuseHandlerインスタンス（オプション）
        """
        # 新アーキテクチャ: 統合ノード使用
        self.sorted_task_extractor_router = SortedTaskExtractorAndRouterNode(llm_handler, langfuse_handler)
        self.task_grouper = TaskGrouper()

    def plan_tasks(self, user_input: str) -> Dict[str, Any]:
        """
        ユーザー入力からタスク計画を作成
        最適化ワークフロー: Combined Step 1&2 + Step 3
        従来ワークフロー: Step 1 + Step 2 + Step 3

        Args:
            user_input: ユーザーの自然言語入力

        Returns:
            タスク計画結果
        """
        print(f"🧠 TaskPlanner: ユーザー入力を分析中...")
        print(f"入力: {user_input}")

        return self._plan_tasks_optimized(user_input)

    def _plan_tasks_optimized(self, user_input: str, session_id: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        最適化ワークフロー: SortedTaskExtractorAndRouterNode + TaskGrouper
        LLM呼び出し回数を削減し、トークン効率を向上
        """
        # Combined Step 1&2: 構造化意図抽出・ルーティング・ソート
        sorted_routed_tasks = self.sorted_task_extractor_router.extract_route_and_sort_tasks(user_input, session_id, user_id)

        print(f"✅ 統合タスク処理完了: {len(sorted_routed_tasks)}個のタスクを抽出・ルーティング・ソート")
        for i, task in enumerate(sorted_routed_tasks, 1):
            priority = task.get("priority", "N/A")
            action = task.get("command", {}).get("action", "N/A")
            condition = task.get("command", {}).get("condition", "N/A")
            agent = task.get("target_agent", "N/A")
            print(f"  タスク{i}: 優先度{priority} - {action} ({condition}) -> {agent}")

        # Step 3: タスクグループ化（優先順位ソート済み）
        grouped_tasks = self.task_grouper.group_tasks(sorted_routed_tasks)

        print(f"✅ タスクグループ化完了: {len(grouped_tasks)}個のエージェントグループを作成")

        # 最適化ワークフローの結果を返す
        return {
            "step": "1&2_combined+3",
            "description": "構造化意図抽出・ルーティング・ソート・グループ化完了（最適化版）",
            "sorted_routed_tasks": sorted_routed_tasks,  # Combined Step 1&2の結果
            "grouped_tasks": grouped_tasks,  # Step 3の結果
            "original_input": user_input,
            "workflow_type": "optimized",
            "llm_calls_saved": 1,  # 従来の2回から1回に削減
            "next_steps": [
                "Step 4: タスク排序（実行計画の優先順位付け）",
                "Step 5: 下流AgentManagerへの逐次配信"
            ]
        }
