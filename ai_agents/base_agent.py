import json
from abc import ABC, abstractmethod
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Type
from typing_extensions import deprecated

from dotenv import load_dotenv
from langgraph.constants import START
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from llm.llm_handler import LLMHandler
from utils.langfuse_handler import LangfuseHandler
from ai_agents.intelligent_agent_router import IntelligentAgentRouter, AgentCapability, RoutingDecision
from services.conversation_service import ConversationService
from db.database import get_db

load_dotenv()

# エージェント基底状態定義 - 全エージェント共通の状態管理
class BaseAgentState(TypedDict):
    """
    全エージェント共通の基本状態
    各具象エージェントは必要に応じてこの状態を拡張可能
    """
    messages: Annotated[List[HumanMessage | AIMessage | SystemMessage], add_messages]
    user_input: str
    html_content: Optional[str]
    error_message: Optional[str]
    next_actions: Optional[str]
    session_id: Optional[str]
    user_id: Optional[str]
    agent_type: Optional[str]  # エージェント種別を識別するフィールド
    agent_manager_id: Optional[str]  # Agent Manager ID
    conversation_context: Optional[List[Dict[str, Any]]]  # 会話履歴コンテキスト
    trace_id: Optional[str]  # Langfuse trace ID（評価用）
    conversation_id: Optional[int]  # 会話履歴ID（保存用）

class BaseAgent(ABC):
    """
    全エージェントの基底クラス
    共通の基本機能とワークフローを提供し、マルチエージェント対応のための標準インターフェースを定義
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True, agent_name: str = None, agent_manager_id: str = None):
        """
        エージェント基底初期化

        Args:
            api_key: APIキー
            llm_type: LLMタイプ（省略時はデフォルト）
            use_langfuse: Langfuse使用フラグ
            agent_name: エージェント名（トレーシング用）
            agent_manager_id: Agent Manager ID
        """
        self.api_key = api_key
        self.agent_name = agent_name or self.__class__.__name__
        self.agent_manager_id = agent_manager_id

        # LLMハンドラ初期化 - 動的LLM切り替え対応
        self.llm_handler = LLMHandler(api_key, llm_type)

        # Langfuse初期化 - 統一トレーシング管理
        self.langfuse_handler = LangfuseHandler(use_langfuse=use_langfuse)

        # エージェント固有のツール初期化（子クラスで実装）
        self.tools = self._initialize_tools()

        # ツールマッピング作成
        self.tool_map = {tool.name: tool for tool in self.tools}

        # ツール付きLLM初期化
        self.llm_with_tools = self.llm_handler.get_llm_with_tools(self.tools)
        self.tool_node = ToolNode(self.tools)

        # ワークフローグラフ構築
        self.graph = self._build_workflow_graph()

    @abstractmethod
    def _initialize_tools(self) -> List[Any]:
        """
        エージェント固有のツールを初期化（子クラスで実装必須）

        Returns:
            List[Any]: エージェント固有のツールリスト
        """
        pass

    @abstractmethod
    def _get_system_message_content(self) -> str:
        """
        エージェント固有のシステムメッセージを取得（子クラスで実装必須）

        Returns:
            str: システムメッセージ内容
        """
        pass

    @abstractmethod
    def _get_workflow_name(self) -> str:
        """
        ワークフロー名を取得（トレーシング用、子クラスで実装必須）

        Returns:
            str: ワークフロー名
        """
        pass

    @abstractmethod
    def get_agent_capability(self) -> AgentCapability:
        """
        エージェント能力定義を取得（インテリジェントルーティング用、子クラスで実装必須）

        Returns:
            AgentCapability: エージェント能力定義
        """
        pass

    def _get_state_class(self) -> Type[TypedDict]:
        """
        使用する状態クラスを取得（子クラスでオーバーライド可能）

        Returns:
            Type[TypedDict]: 状態クラス
        """
        return BaseAgentState

    def _load_conversation_context(self, session_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """会話履歴コンテキストを読み込み"""
        try:
            db = next(get_db())

            # セッション履歴を取得
            session_history = ConversationService.get_session_history(db, session_id, limit=10)

            # 異なるエージェント間での履歴も取得
            cross_agent_history = ConversationService.get_cross_agent_history(
                db, 
                session_id=session_id, 
                user_id=user_id,
                agent_manager_id=self.agent_manager_id,
                limit=5
            )

            # 履歴をマージして重複を除去
            all_history = list({conv.id: conv for conv in (session_history + cross_agent_history)}.values())
            all_history.sort(key=lambda x: x.created_at, reverse=True)

            return ConversationService.format_history_for_context(all_history[:15])

        except Exception as e:
            print(f"会話履歴の読み込みに失敗: {str(e)}")
            return []

    def _assistant_node(self, state: BaseAgentState):
        """
        基本アシスタントノード - システムメッセージとLLM呼び出しを処理
        子クラスでオーバーライド可能
        """
        # 会話履歴コンテキストを読み込み
        if state.get("session_id") and not state.get("conversation_context"):
            state["conversation_context"] = self._load_conversation_context(
                state["session_id"], 
                state.get("user_id")
            )

        # エージェント固有のシステムメッセージを取得
        sys_msg_content = self._get_system_message_content()

        # 会話履歴コンテキストをシステムメッセージに追加
        if state.get("conversation_context"):
            context_summary = self._format_context_for_system_message(state["conversation_context"])
            sys_msg_content += f"\n\n## 会話履歴コンテキスト:\n{context_summary}"

        sys_msg = SystemMessage(content=sys_msg_content)

        # エージェント種別を状態に設定
        state["agent_type"] = self.agent_name
        state["agent_manager_id"] = self.agent_manager_id

        # LLMを呼び出してメッセージに追加
        response = self.llm_with_tools.invoke([sys_msg] + state["messages"])
        state["messages"].append(response)

        return state

    def _format_context_for_system_message(self, context: List[Dict[str, Any]]) -> str:
        """会話コンテキストをシステムメッセージ用にフォーマット"""
        if not context:
            return "（履歴なし）"

        formatted_lines = []
        for item in context[:5]:  # 最新5件のみ
            timestamp = item.get("timestamp", "")
            agent = item.get("agent_type", "unknown")
            user_msg = item.get("user_message", "")
            agent_resp = item.get("agent_response", "")

            formatted_lines.append(f"[{timestamp[:19]}] {agent}: {user_msg} → {agent_resp}")

        return "\n".join(formatted_lines)

    def _save_conversation(self, state: BaseAgentState, final_response: str):
        """会話履歴を保存してconversation_idを状態に設定"""
        try:
            if not state.get("session_id"):
                return

            db = next(get_db())

            # レスポンスデータを解析
            html_content = state.get("html_content")
            error_info = state.get("error_message")
            next_actions = state.get("next_actions")

            # trace_idをcontext_dataに含める
            context_data = {}
            if state.get("trace_id"):
                context_data["trace_id"] = state["trace_id"]

            # 会話履歴を保存してconversation_idを取得
            conversation = ConversationService.save_conversation(
                db=db,
                session_id=state["session_id"],
                user_id=state.get("user_id"),
                agent_type=self.agent_name,
                agent_manager_id=self.agent_manager_id,
                user_message=state["user_input"],
                agent_response=final_response,
                message_type='chat',
                llm_type=self.llm_type,
                html_content=html_content,
                error_info=error_info,
                next_actions=next_actions,
                context_data=context_data if context_data else None
            )

            # conversation_idを状態に保存
            state["conversation_id"] = conversation.id
            print(f"✅ 会話履歴を保存しました: ID={conversation.id}")

        except Exception as e:
            print(f"⚠️ 会話履歴の保存に失敗: {str(e)}")

    # [既存のメソッドは変更なし - _build_workflow_graph, _create_initial_state, etc.]
    def _build_workflow_graph(self) -> CompiledStateGraph:
        """
        基本ワークフローグラフを構築 - 標準的なassistant->tools->assistantフロー
        子クラスでオーバーライドして独自ワークフローを実装可能
        """
        # 状態グラフを定義
        state_class = self._get_state_class()
        builder = StateGraph(state_class)

        # 基本ノードを追加
        builder.add_node("assistant", self._assistant_node)
        builder.add_node("tools", self.tool_node)

        # 基本エッジを定義
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant",
            tools_condition,  # ツールが必要な場合はtools、そうでなければ終了
        )
        builder.add_edge("tools", "assistant")

        return builder.compile()

    def _create_initial_state(self, command: str, session_id: str = None, user_id: str = None) -> BaseAgentState:
        """
        初期状態を作成 - 子クラスでオーバーライド可能

        Args:
            command: ユーザーコマンド
            session_id: セッションID
            user_id: ユーザーID

        Returns:
            BaseAgentState: 初期状態
        """
        state_class = self._get_state_class()
        return state_class(
            messages=[HumanMessage(content=command)],
            user_input=command,
            html_content=None,
            error_message=None,
            next_actions=None,
            session_id=session_id,
            user_id=user_id,
            agent_type=self.agent_name,
            agent_manager_id=self.agent_manager_id,
            conversation_context=None,
            trace_id=None
        )

    def _process_final_state(self, final_state: BaseAgentState) -> Dict[str, Any]:
        """
        最終状態を処理してレスポンスを構築 - 子クラスでオーバーライド可能

        Args:
            final_state: 最終状態

        Returns:
            Dict[str, Any]: レスポンスデータ
        """
        response_message = final_state["messages"][-1].content if final_state["messages"] else "処理が完了しました"

        # 会話履歴を保存（conversation_idが状態に設定される）
        self._save_conversation(final_state, response_message)

        response_data = {
            "message": response_message,
            "html_content": final_state.get("html_content"),
            "next_actions": final_state.get("next_actions"),
            "llm_type_used": self.llm_type,
            "llm_info": self.get_llm_info(),
            "agent_type": self.agent_name,
            "agent_manager_id": self.agent_manager_id,
            "trace_id": final_state.get("trace_id"),  # Langfuse trace IDを追加
            "conversation_id": final_state.get("conversation_id")  # 会話履歴IDを追加
        }

        if final_state.get("error_message"):
            response_data["error"] = final_state["error_message"]

        return response_data

    def switch_llm(self, new_llm_type: str):
        """LLMタイプを実行時に切り替え"""
        self.llm_handler.switch_llm(new_llm_type)
        # ツール付きLLMも更新
        self.llm_with_tools = self.llm_handler.get_llm_with_tools(self.tools)

    def get_available_llms(self) -> List[str]:
        """利用可能なLLMのリストを取得"""
        return self.llm_handler.get_available_llms()

    def get_llm_info(self, llm_type: str = None) -> Dict[str, Any]:
        """LLM情報を取得"""
        return self.llm_handler.get_llm_info(llm_type)

    @property
    def llm_type(self) -> str:
        """現在のLLMタイプを取得"""
        return self.llm_handler.get_current_llm_type()

    def get_agent_info(self) -> Dict[str, Any]:
        """エージェント情報を取得"""
        return {
            "agent_name": self.agent_name,
            "agent_type": self.__class__.__name__,
            "agent_manager_id": self.agent_manager_id,
            "tools_count": len(self.tools),
            "tool_names": [tool.name for tool in self.tools],
            "llm_type": self.llm_type,
            "llm_info": self.get_llm_info()
        }

    def process_command(self, command: str, llm_type: str = None, session_id: str = None, user_id: str = None) -> str:
        """
        ユーザーコマンドを処理 - 統一インターフェース

        Args:
            command: ユーザーコマンド
            llm_type: LLMタイプ（省略時は現在のLLMを使用）
            session_id: セッションID
            user_id: ユーザーID

        Returns:
            str: JSON形式のレスポンス
        """
        # observeデコレータを取得（Langfuseが利用可能な場合のみ適用）
        workflow_name = self._get_workflow_name()
        observe_decorator = self.langfuse_handler.observe_decorator(workflow_name)

        @observe_decorator
        def _execute_workflow():
            trace_id = None
            try:
                # LLMタイプが指定された場合は切り替え
                if llm_type and llm_type != self.llm_type:
                    self.switch_llm(llm_type)

                # 初期状態を作成
                initial_state = self._create_initial_state(command, session_id, user_id)

                # ワークフローを実行（CallbackHandlerを使用）
                config = self.langfuse_handler.get_config(workflow_name, session_id, user_id)
                final_state = self.graph.invoke(initial_state, config=config)

                # ワークフロー実行後にtrace_idを取得
                trace_id = self.langfuse_handler.get_current_trace_id()

                # trace_idを最終状態に保存
                final_state["trace_id"] = trace_id

                # レスポンスを構築
                response_data = self._process_final_state(final_state)

                return json.dumps(response_data, ensure_ascii=False, indent=2)

            except Exception as e:
                error_msg = f"ワークフロー実行に失敗しました: {str(e)}"

                # エラー時もtrace_idを取得を試行
                if not trace_id:
                    trace_id = self.langfuse_handler.get_current_trace_id()

                return json.dumps({
                    "message": error_msg,
                    "error": str(e),
                    "llm_type_used": self.llm_type,
                    "llm_info": self.get_llm_info(),
                    "agent_type": self.agent_name,
                    "agent_manager_id": self.agent_manager_id,
                    "trace_id": trace_id
                }, ensure_ascii=False)

        return _execute_workflow()

@deprecated(
    "IntelligentMultiAgentOrchestrator is deprecated. Use BaseAgent directly for multi-agent systems.",
)
class IntelligentMultiAgentOrchestrator:
    """
    インテリジェントマルチエージェント統合管理クラス
    LLMベースの知的ルーティングで複数のエージェントを統合管理し、適切なエージェントに処理を委譲
    """

    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True, manager_id: str = None):
        """
        インテリジェントマルチエージェント統合管理初期化

        Args:
            api_key: APIキー
            llm_type: LLMタイプ
            use_langfuse: Langfuse使用フラグ
            manager_id: マネージャーID
        """
        self.agents: Dict[str, BaseAgent] = {}
        self.manager_id = manager_id or f"manager_{id(self)}"

        # インテリジェントルーターを初期化
        self.intelligent_router = IntelligentAgentRouter(
            api_key=api_key,
            llm_type=llm_type,
            use_langfuse=use_langfuse
        )

    def _save_collaboration_history(self, 
                                   session_id: str, 
                                   user_id: Optional[str],
                                   command: str, 
                                   routing_decision: RoutingDecision,
                                   collaboration_results: List[Dict[str, Any]]):
        """協作履歴を保存"""
        try:
            db = next(get_db())

            ConversationService.save_conversation(
                db=db,
                session_id=session_id,
                user_id=user_id,
                agent_type="collaboration_manager",
                agent_manager_id=self.manager_id,
                user_message=command,
                agent_response=json.dumps(collaboration_results, ensure_ascii=False),
                message_type='collaboration',
                is_collaboration=True,
                collaboration_agents=[{"agent_type": result["agent_type"]} for result in collaboration_results],
                routing_decision=routing_decision.model_dump() if routing_decision else None
            )
        except Exception as e:
            print(f"協作履歴の保存に失敗: {str(e)}")

    def register_agent(self, agent_type: str, agent: BaseAgent):
        """
        エージェントを登録し、その能力定義をルーターに登録

        Args:
            agent_type: エージェントタイプ
            agent: エージェントインスタンス
        """
        # エージェントにマネージャーIDを設定
        agent.agent_manager_id = self.manager_id

        self.agents[agent_type] = agent

        # エージェント能力をルーターに登録
        capability = agent.get_agent_capability()
        self.intelligent_router.register_agent_capability(capability)

    def get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """エージェントを取得"""
        return self.agents.get(agent_type)

    def route_command_intelligently(self, command: str, context: Dict[str, Any] = None) -> RoutingDecision:
        """
        LLMベースでコマンドを分析して最適なエージェントを決定

        Args:
            command: ユーザーコマンド
            context: 追加コンテキスト情報

        Returns:
            RoutingDecision: ルーティング決定結果
        """
        return self.intelligent_router.route_command(command, context)

    def process_command(self, command: str, agent_type: str = None, context: Dict[str, Any] = None, **kwargs) -> str:
        """
        コマンドを処理 - インテリジェントルーティングで適切なエージェントに委譲

        Args:
            command: ユーザーコマンド
            agent_type: 指定エージェントタイプ（省略時はインテリジェントルーティング）
            context: 追加コンテキスト情報
            **kwargs: その他のパラメータ

        Returns:
            str: JSON形式のレスポンス
        """
        # エージェントタイプが指定されていない場合はインテリジェントルーティング
        routing_decision = None
        if not agent_type:
            routing_decision = self.route_command_intelligently(command, context)
            agent_type = routing_decision.selected_agent

        # エージェントを取得
        agent = self.get_agent(agent_type)
        if not agent:
            error_response = {
                "error": f"エージェントタイプ '{agent_type}' が見つかりません",
                "available_agents": list(self.agents.keys())
            }

            if routing_decision:
                error_response.update({
                    "routing_decision": routing_decision.model_dump(),
                    "alternative_agents": routing_decision.alternative_agents
                })

            return json.dumps(error_response, ensure_ascii=False)

        # エージェントに処理を委譲
        result = agent.process_command(command, **kwargs)

        # ルーティング情報を結果に追加
        if routing_decision:
            result_data = json.loads(result)
            result_data["routing_decision"] = routing_decision.model_dump()
            result = json.dumps(result_data, ensure_ascii=False, indent=2)

        return result

    def process_collaborative_command(self, command: str, context: Dict[str, Any] = None, **kwargs) -> str:
        """
        複数エージェント連携が必要なコマンドを処理

        Args:
            command: ユーザーコマンド
            context: 追加コンテキスト情報
            **kwargs: その他のパラメータ

        Returns:
            str: JSON形式のレスポンス
        """
        routing_decision = self.route_command_intelligently(command, context)

        if not routing_decision.requires_collaboration:
            # 単一エージェントで処理
            return self.process_command(command, routing_decision.selected_agent, context, **kwargs)

        # 複数エージェント連携処理
        collaboration_results = []
        for agent_type in routing_decision.collaboration_sequence:
            agent = self.get_agent(agent_type)
            if agent:
                result = agent.process_command(command, **kwargs)
                collaboration_results.append({
                    "agent_type": agent_type,
                    "result": json.loads(result)
                })

        # 協作履歴を保存
        self._save_collaboration_history(
            kwargs.get("session_id"),
            kwargs.get("user_id"),
            command,
            routing_decision,
            collaboration_results
        )

        return json.dumps({
            "collaboration_mode": True,
            "routing_decision": routing_decision.model_dump(),
            "collaboration_results": collaboration_results,
            "final_message": "複数エージェント連携処理が完了しました",
            "agent_manager_id": self.manager_id
        }, ensure_ascii=False, indent=2)

    def get_all_agents_info(self) -> Dict[str, Any]:
        """全エージェントの情報を取得"""
        return {
            agent_type: agent.get_agent_info() 
            for agent_type, agent in self.agents.items()
        }

    def get_routing_analytics(self) -> Dict[str, Any]:
        """ルーティング分析情報を取得"""
        return self.intelligent_router.get_routing_analytics()

    def provide_routing_feedback(self, command: str, predicted_agent: str, actual_agent: str, success: bool, user_feedback: str = None):
        """ルーティング結果のフィードバックを提供"""
        self.intelligent_router.update_routing_feedback(command, predicted_agent, actual_agent, success, user_feedback)
