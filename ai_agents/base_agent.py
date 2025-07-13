import json
from abc import ABC, abstractmethod
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Type

from dotenv import load_dotenv
from langchain_core.messages import ToolMessage
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

# エージェント基底状態定義 - 全エージェント共通の状態管理（多層Agent間状態互通対応）
class BaseAgentState(TypedDict):
    """
    全エージェント共通の基本状態（多層Agent間での状態共有対応）
    各具象エージェントは必要に応じてこの状態を拡張可能
    """
    messages: Annotated[List[HumanMessage | AIMessage | SystemMessage], add_messages]
    user_input: str
    html_content: Optional[str]
    error_message: Optional[str]
    next_actions: Optional[str | List[str]]  # 次のアクション（文字列またはアクションリスト）
    session_id: Optional[str]
    user_id: Optional[str]
    agent_type: Optional[str]  # エージェント種別を識別するフィールド
    agent_manager_id: Optional[str]  # Agent Manager ID
    conversation_context: Optional[List[Dict[str, Any]]]  # 会話履歴コンテキスト
    trace_id: Optional[str]  # Langfuse trace ID（評価用）
    conversation_id: Optional[int]  # 会話履歴ID（保存用）
    is_entry_agent: Optional[bool]  # エントリーエージェントかどうか（初期状態設定用）

    # 多層Agent間状態互通用の追加フィールド
    llm_type_used: Optional[str]  # 使用されたLLMタイプ
    llm_info: Optional[Dict[str, Any]]  # LLM情報
    agent_name: Optional[str]  # エージェント名
    response_message: Optional[str]  # レスポンスメッセージ
    response_data: Optional[Dict[str, Any]]  # 後方互換性用のレスポンスデータ

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
    def _get_system_message_content(self, is_entry_agent: bool = True) -> str:
        """
        エージェント固有のシステムメッセージを取得（子クラスで実装必須）

        Args:
            is_entry_agent: エントリーエージェントかどうか（初期状態設定用）

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

    def get_state_class(self) -> Type[TypedDict]:
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
        sys_msg_content = self._get_system_message_content(state.get("is_entry_agent", True))

        # 会話履歴コンテキストを読み込み
        if state.get("session_id") and not state.get("conversation_context"):
            state["conversation_context"] = self._load_conversation_context(
                state["session_id"],
                state.get("user_id")
            )

        # 会話履歴コンテキストをシステムメッセージに追加
        if state.get("conversation_context"):
            context_summary = self._format_context_for_system_message(state["conversation_context"])
            sys_msg_content += f"\n\n## Conversation history context:\n{context_summary}"

        sys_msg = SystemMessage(content=sys_msg_content)

        # エージェント種別を状態に設定
        state["agent_type"] = self.agent_name
        state["agent_manager_id"] = self.agent_manager_id

        # LLMを呼び出してメッセージに追加
        response = self.llm_with_tools.invoke([sys_msg] + state["messages"])
        response_content = response.content.strip()
        from utils.string_utils import clean_think_output
        response_content, thoughts = clean_think_output(response_content)
        if thoughts:
            print("\n🤔 LLM Thoughts:")
            print(thoughts)

        # JSONブロックを探す（```json...```の形式も対応）
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

        # レスポンス内容をJSONとして解析
        try:
            content_dict = json.loads(json_content)
            if isinstance(content_dict, dict):
                if "html_content" in content_dict:
                    state["html_content"] = content_dict["html_content"]
                if "next_actions" in content_dict:
                    state["next_actions"] = content_dict["next_actions"]
                if "error" in content_dict:
                    state["error_message"] = content_dict.get("error")
        except json.JSONDecodeError:
            pass

        response.content = json_content
        print(f"\n💬 {self.agent_name} Response:\n{json_content}")

        state["messages"].append(response)

        return state

    def _custom_tool_node(self, state: BaseAgentState):
        """
        カスタムツールノード - session_idとuser_idを状態から取得してツールに渡す
        """

        last_message = state["messages"][-1]

        # tool_callsが存在しない場合は何もしない
        if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
            return state

        outputs = []

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            try:
                # ツール呼び出しの引数に状態情報を追加
                # BaseAgentToolの実例かどうかを判断
                if tool_name in self.tool_map:
                    tool_instance = self.tool_map[tool_name]

                    # BaseAgentToolの実例の場合のみshared_stateを渡す
                    from ai_agents.base_agent_tool import BaseAgentTool

                    if isinstance(tool_instance, BaseAgentTool):
                        # downstream_command = json.dumps({
                        #     "command": {
                        #         "action": tool_args["command"],
                        #         "condition": tool_args["command"]
                        #     }
                        # }, ensure_ascii=False, indent=2)
                        from utils.string_utils import state_to_json
                        tool_args["shared_state"] = state_to_json(
                            self._create_downstream_state(shared_state=state, command=None))

                    if state.get("session_id"):
                        tool_args["session_id"] = state["session_id"]
                    if state.get("user_id"):
                        tool_args["user_id"] = state["user_id"]
                    if state.get("is_entry_agent"):
                        tool_args["is_entry_agent"] = False
                    # TODO: ユーザー入力をツールに渡すかどうかは要検討
                    # if state.get("user_input"):
                    #     tool_args["user_input"] = state["user_input"]

                    # ツールを実行
                    tool_response = tool_instance.invoke(tool_args)
                    print(f"🔧 Tool '{tool_name}' response type: {type(tool_response)}")
                    print(f"🔧 Tool '{tool_name}' invoked with args: {tool_args}, original response: {tool_response}")
                    if isinstance(tool_instance, BaseAgentTool):
                        if isinstance(tool_response, dict):
                            tool_response = tool_response["messages"][-1].content if tool_response[
                                "messages"] else f"⚠️ [{tool_name}]処理が完了しました。結果なし。"  # BaseAgentToolの場合は最後のメッセージを取得
                        else:
                            tool_response = str(tool_response)
                        print(f"🔧 Tool '{tool_name}' parsed response: {tool_response}")

                    # ツールの実行結果をToolMessageとして作成
                    tool_message = ToolMessage(
                        content=str(tool_response),
                        tool_call_id=tool_call_id
                    )

                    outputs.append(tool_message)
                    print(f"✅ Tool '{tool_name}' executed successfully")

                else:
                    # ツールが存在しない場合のエラーレスポンス
                    error_message = ToolMessage(
                        content=f"Error: Tool '{tool_name}' not found in available tools",
                        tool_call_id=tool_call_id
                    )
                    outputs.append(error_message)
                    print(f"❌ Tool '{tool_name}' not found in tool_map")

            except Exception as e:
                # ツール実行エラー時のレスポンス
                error_message = ToolMessage(
                    content=f"Error executing tool '{tool_name}': {str(e)}",
                    tool_call_id=tool_call_id
                )
                outputs.append(error_message)
                print(f"❌ Tool execution error for '{tool_name}': {e}")

        return {"messages": outputs}

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
        state_class = self.get_state_class()
        builder = StateGraph(state_class)

        # 基本ノードを追加
        builder.add_node("assistant", self._assistant_node)
        builder.add_node("tools", self._custom_tool_node)
        # builder.add_node("tools", self.tool_node)

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
        state_class = self.get_state_class()
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

    def _create_downstream_state(self, shared_state: BaseAgentState, command: str = None, user_input: str = None) -> BaseAgentState:
        """
        下流Agent用の状態を作成（上流から渡された共有状態をベース）

        Args:
            shared_state: 上流Agentから渡された共有状態
            command: 新しいコマンド
            user_input: ユーザーのオリジナル入力内容

        Returns:
            BaseAgentState: 下流Agent用の状態
        """
        # 共有状態をコピーして新しいメッセージを追加
        state_class = self.get_state_class()

        # 既存のメッセージリストに新しいメッセージを追加
        # existing_messages = shared_state.get("messages", [])
        # new_messages = existing_messages + [HumanMessage(content=command)]
        if command:
            new_messages = [HumanMessage(content=command)]

            # 共有状態をベースに新しい状態を作成
            downstream_state = state_class({
                **shared_state,  # 既存の共有状態をすべて継承
                "messages": new_messages,  # 新しいメッセージを追加
                "agent_type": self.agent_name,  # 現在のエージェント名に更新
                "agent_manager_id": self.agent_manager_id,  # 現在のエージェントマネージャーIDに更新
                "is_entry_agent": False,  # 下流Agentなのでfalse
            })
        else:
            # コマンドがない場合は共有状態をそのまま使用 TODO: AgentManagerでのcommand分解処理を検討
            downstream_state = state_class({
                **shared_state,  # 既存の共有状態をすべて継承
                "agent_type": self.agent_name,  # 現在のエージェント名に更新
                "agent_manager_id": self.agent_manager_id,  # 現在のエージェントマネージャーIDに更新
                "is_entry_agent": False,  # 下流Agentなのでfalse
            })

        return downstream_state

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
            "error_message": final_state.get("error_message"),
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

    def process_command(self, command: str, user_input: str = None, llm_type: str = None, session_id: str = None, user_id: str = None, is_entry_agent: bool = False, shared_state: BaseAgentState = None) -> BaseAgentState:
        """
        ユーザーコマンドを処理 - 統一インターフェース（多層Agent間状態互通対応）

        Args:
            command: ユーザーコマンド
            user_input: ユーザーのオリジナル入力内容（省略時はコマンドを使用）
            llm_type: LLMタイプ（省略時は現在のLLMを使用）
            session_id: セッションID
            user_id: ユーザーID
            is_entry_agent: エントリーエージェントかどうか（初期状態の設定に影響）
            shared_state: 上流Agentから渡された共有状態（下流Agentの場合に使用）

        Returns:
            BaseAgentState: エージェント実行結果の状態オブジェクト（多層Agent間での状態共有用）
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

                # 初期状態を作成または共有状態を利用
                if is_entry_agent:
                    # エントリーAgentの場合：新しい初期状態を作成
                    initial_state = self._create_initial_state(command, user_input, session_id, user_id, is_entry_agent)
                else:
                    # 下流Agentの場合：上流から渡された共有状態を利用
                    if shared_state is None:
                        # shared_stateが渡されていない場合は新しい状態を作成（後方互換性）
                        initial_state = self._create_initial_state(command, user_input, session_id, user_id, is_entry_agent)
                    else:
                        # 共有状態をベースに新しいメッセージを追加
                        initial_state = self._create_downstream_state(shared_state, command, user_input)

                # ワークフローを実行（CallbackHandlerを使用）
                config = self.langfuse_handler.get_config(workflow_name, session_id, user_id)
                final_state = self.graph.invoke(initial_state, config=config)

                # ワークフロー実行後にtrace_idを取得
                trace_id = self.langfuse_handler.get_current_trace_id()

                # trace_idを最終状態に保存
                final_state["trace_id"] = trace_id

                # 最終状態を処理してレスポンスデータを構築
                response_data = self._process_final_state(final_state)

                # BaseAgentStateに必要な追加フィールドを設定
                final_state.update({
                    "llm_type_used": self.llm_type,
                    "llm_info": self.get_llm_info(),
                    "agent_name": self.agent_name,
                    "response_message": response_data.get("message", ""),
                    "response_data": response_data  # 後方互換性のため
                })

                return final_state

            except Exception as e:
                error_msg = f"ワークフロー実行に失敗しました: {str(e)}"

                # エラー時もtrace_idを取得を試行
                if not trace_id:
                    trace_id = self.langfuse_handler.get_current_trace_id()

                # エラー時のBaseAgentState構築
                error_state = self.get_state_class()({
                    "messages": [],
                    "user_input": user_input or command,
                    "html_content": None,
                    "error_message": error_msg,
                    "next_actions": None,
                    "session_id": session_id,
                    "user_id": user_id,
                    "agent_type": self.agent_name,
                    "agent_manager_id": self.agent_manager_id,
                    "conversation_context": None,
                    "trace_id": trace_id,
                    "conversation_id": None,
                    "is_entry_agent": is_entry_agent,
                    "llm_type_used": self.llm_type,
                    "llm_info": self.get_llm_info(),
                    "agent_name": self.agent_name,
                    "response_message": error_msg,
                    "response_data": {
                        "message": error_msg,
                        "error": str(e),
                        "llm_type_used": self.llm_type,
                        "llm_info": self.get_llm_info(),
                        "agent_type": self.agent_name,
                        "agent_manager_id": self.agent_manager_id,
                        "trace_id": trace_id
                    }
                })

                return error_state

        return _execute_workflow()

    def generate_tool_descriptions(self) -> str:
        """Generate dynamic tool descriptions from bound tools"""
        if not hasattr(self, 'tools') or not self.tools:
            return "    No tools available"

        descriptions = []
        for i, tool in enumerate(self.tools, 1):
            # Get tool name and description
            tool_name = getattr(tool, 'name', 'Unknown Tool')
            tool_description = getattr(tool, 'description', 'No description available')

            # Start with basic tool info
            tool_info = f"    {i}. **{tool_name}**: {tool_description}"
            
            # Add parameter information if available
            if hasattr(tool, 'args_schema') and tool.args_schema:
                try:
                    # Get field information from Pydantic model
                    if hasattr(tool.args_schema, 'model_fields'):
                        # Pydantic v2
                        fields = tool.args_schema.model_fields
                    elif hasattr(tool.args_schema, '__fields__'):
                        # Pydantic v1
                        fields = tool.args_schema.__fields__
                    else:
                        fields = {}
                    
                    if fields:
                        tool_info += "\n       Parameters:"
                        for field_name, field_info in fields.items():
                            # Extract field description and type
                            if hasattr(field_info, 'description'):
                                # Pydantic v2
                                field_desc = field_info.description or "No description"
                                field_type = getattr(field_info, 'annotation', 'Any')
                            elif hasattr(field_info, 'field_info'):
                                # Pydantic v1
                                field_desc = field_info.field_info.description or "No description"
                                field_type = field_info.type_
                            else:
                                field_desc = "No description"
                                field_type = "Any"
                            
                            # Format field type for display
                            if hasattr(field_type, '__name__'):
                                type_name = field_type.__name__
                            else:
                                type_name = str(field_type)
                            
                            tool_info += f"\n         - {field_name} ({type_name}): {field_desc}"
                except Exception as e:
                    # If parameter extraction fails, just show basic info
                    tool_info += f"\n       Parameters: (Error extracting parameter info: {str(e)})"
            
            descriptions.append(tool_info)

        return "\n".join(descriptions)

    def _merge_downstream_agent_capabilities(self) -> AgentCapability:
        """
        下流Agentの能力を一つのAgentCapabilityオブジェクトに合併

        Returns:
            AgentCapability: 合併後の能力オブジェクト
        """
        # ツール説明を取得
        description = self.generate_tool_descriptions()

        # 全ての下流Agentの能力情報を収集
        all_primary_domains = []
        all_key_functions = []
        all_example_commands = []
        all_collaboration_needs = []

        # 全てのツールを遍歴し、そのAgentの能力を取得
        for tool in self.tools:
            if hasattr(tool, 'agent') and hasattr(tool.agent, 'get_agent_capability'):
                try:
                    capability = tool.agent.get_agent_capability()
                    if capability:
                        # primary_domainsを収集
                        if hasattr(capability, 'primary_domains') and capability.primary_domains:
                            all_primary_domains.extend(capability.primary_domains)

                        # key_functionsを収集
                        if hasattr(capability, 'key_functions') and capability.key_functions:
                            all_key_functions.extend(capability.key_functions)

                        # example_commandsを収集
                        if hasattr(capability, 'example_commands') and capability.example_commands:
                            all_example_commands.extend(capability.example_commands)

                        # collaboration_needsを収集
                        if hasattr(capability, 'collaboration_needs') and capability.collaboration_needs:
                            all_collaboration_needs.extend(capability.collaboration_needs)

                except Exception as e:
                    # エラーを記録するが処理を中断しない
                    print(f"警告: {tool.__class__.__name__}から能力取得に失敗しました: {str(e)}")

        # 各フィールドを重複除去
        unique_primary_domains = list(set(all_primary_domains))
        unique_key_functions = list(set(all_key_functions))
        unique_example_commands = list(set(all_example_commands))
        unique_collaboration_needs = list(set(all_collaboration_needs))

        # 合併後のAgentCapabilityを作成
        merged_capability = AgentCapability(
            agent_type=self.agent_name,
            description=description,
            primary_domains=unique_primary_domains,
            key_functions=unique_key_functions,
            example_commands=unique_example_commands,
            collaboration_needs=unique_collaboration_needs
        )

        return merged_capability