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

from ai_agents.intelligent_agent_router import AgentCapability
from llm.llm_handler import LLMHandler
from utils.langfuse_handler import LangfuseHandler
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
    is_entry_agent: Optional[bool]  # エントリーエージェントかどうか（初期状態設定用）

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
        # エージェント固有のシステムメッセージを取得
        sys_msg_content = self._get_system_message_content()

        # 会話履歴コンテキストを読み込み
        if state.get("session_id") and not state.get("conversation_context"):
            state["conversation_context"] = self._load_conversation_context(
                state["session_id"],
                state.get("user_id")
            )

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

    def _custom_tool_node(self, state: BaseAgentState):
        """
        カスタムツールノード - session_idとuser_idを状態から取得してツールに渡す
        重複ツール呼び出しを防止する機能を追加
        """
        from langchain_core.messages import ToolMessage

        for tool_call in state["messages"][-1].tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            # 状態からsession_idとuser_idを取得してツール引数に追加
            if state.get("session_id"):
                tool_args["session_id"] = state["session_id"]
            if state.get("user_id"):
                tool_args["user_id"] = state["user_id"]
            if state.get("is_entry_agent"):
                tool_args["is_entry_agent"] = False
            if state.get("user_input"):
                tool_args["user_input"] = state["user_input"]


            # ツールを実行
            response = self.tool_map[tool_name].invoke(tool_args)
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

    def _build_workflow_graph(self) -> CompiledStateGraph:
        """
        基本ワークフローグラフを構築 - 標準的なassistant->tools->assistantフロー
        子クラスでオーバーライドして独自ワークフローを実装可能
        重複ツール呼び出し防止機能を含む
        """
        # 状態グラフを定義
        state_class = self._get_state_class()
        builder = StateGraph(state_class)

        # 基本ノードを追加
        builder.add_node("assistant", self._assistant_node)
        builder.add_node("tools", self._custom_tool_node)

        # 基本エッジを定義
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant",
            tools_condition,
        )
        builder.add_edge("tools", "assistant")

        return builder.compile()

    def _create_initial_state(self, command: str, user_input: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False) -> BaseAgentState:
        """
        初期状態を作成 - 子クラスでオーバーライド可能

        Args:
            command: ユーザーコマンド
            user_input: ユーザーのオリジナル入力内容（省略時はコマンドを使用）
            session_id: セッションID
            user_id: ユーザーID
            is_entry_agent: エントリーエージェントかどうか（初期状態設定用）

        Returns:
            BaseAgentState: 初期状態
        """
        state_class = self._get_state_class()
        return state_class(
            messages=[HumanMessage(content=command)],
            user_input=user_input or command,  # user_inputがNoneの場合はcommandを使用
            html_content=None,
            error_message=None,
            next_actions=None,
            session_id=session_id,
            user_id=user_id,
            agent_type=self.agent_name,
            agent_manager_id=self.agent_manager_id,
            conversation_context=None,
            trace_id=None,
            is_entry_agent=is_entry_agent,
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
        if final_state.get("is_entry_agent"):
            # エントリーエージェントの場合は、会話履歴を保存
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

    def process_command(self, command: str, user_input: str = None, llm_type: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False) -> str:
        """
        ユーザーコマンドを処理 - 統一インターフェース

        Args:
            command: ユーザーコマンド
            user_input: ユーザーのオリジナル入力内容（省略時はコマンドを使用）
            llm_type: LLMタイプ（省略時は現在のLLMを使用）
            session_id: セッションID
            user_id: ユーザーID
            is_entry_agent: エントリーエージェントかどうか（初期状態の設定に影響）

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
                initial_state = self._create_initial_state(command, user_input, session_id, user_id, is_entry_agent)

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
