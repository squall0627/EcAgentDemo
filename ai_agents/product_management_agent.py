import os
import json
from typing import TypedDict, Annotated, List, Dict, Any, Optional

from langfuse import Langfuse
from typing_extensions import Literal
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from ai_agents.tools.product_tools import (
    SearchProductsTool,
    UpdateStockTool,
    UpdateCategoryTool,
    BulkUpdateStockTool,
    ValidateProductTool,
    GenerateHtmlTool,
    PublishProductsTool,
    UnpublishProductsTool
)

# Langfuse V3
LANGFUSE_AVAILABLE = False

try:
    # Langfuse V3 最新的CallbackHandler导入方式
    from langfuse.langchain import CallbackHandler
    from langfuse import observe

    LANGFUSE_AVAILABLE = True
    print("✅ Langfuse V3 CallbackHandler successfully imported from langfuse.langchain")
except ImportError as e:
    print(f"❌ Langfuse V3 CallbackHandler not available: {e}")
    # # 创建空的CallbackHandler和observe装饰器
    # class MockCallbackHandler:
    #     def __init__(self, *args, **kwargs):
    #         pass
    #
    # CallbackHandler = MockCallbackHandler
    #
    # def observe(name=None, **kwargs):
    #     def decorator(func):
    #         return func
    #     return decorator
    
    LANGFUSE_AVAILABLE = False

# サンプルコマンド
EXAMPLE_COMMANDS = [
    "コーヒー商品を検索してください",
    "在庫が10未満の商品を表示してください", 
    "JANコード123456789の在庫を50に設定してください",
    "商品のカテゴリーを飲料に変更してください",
    "在庫切れ商品を自動補充してください",
    "全ての商品の在庫を100に設定してください",
    "商品を棚上げしてください",
    "商品を棚下げしてください"
]

# LangGraph状態定義
class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | SystemMessage], add_messages]
    current_step: str
    user_input: str
    search_results: Optional[List[Dict]]
    validation_results: Optional[Dict]
    selected_products: Optional[List[Dict]]
    action_type: Optional[str]
    html_content: Optional[str]
    error_message: Optional[str]
    next_actions: Optional[List[str]]
    session_id: Optional[str]
    user_id: Optional[str]
    intermediate_steps: List[Dict]

class ProductManagementLangGraphAgent:
    def __init__(self, api_key: str, use_langfuse: bool = True):
        """LangGraphベースの商品管理エージェントを初期化"""
        self.api_key = api_key
        self.use_langfuse = use_langfuse and LANGFUSE_AVAILABLE
        
        # Langfuse V3 CallbackHandler初期化
        self.langfuse_handler = None
        if self.use_langfuse:
            try:
                # 環境変数チェック
                public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
                secret_key = os.getenv("LANGFUSE_SECRET_KEY")
                host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

                if not public_key or not secret_key:
                    print("⚠️  Langfuse credentials not found in environment variables")
                    self.use_langfuse = False
                else:
                    # Langfuse V3 CallbackHandlerを初期化
                    Langfuse(
                        public_key=public_key,
                        secret_key=secret_key,
                        host=host
                    )
                    self.langfuse_handler = CallbackHandler()
                    print("✅ Langfuse V3 CallbackHandler initialized successfully")
                    
            except Exception as e:
                print(f"❌ Failed to initialize Langfuse V3 CallbackHandler: {e}")
                self.use_langfuse = False
        else:
            print("💡 Running without Langfuse tracing")
        
        # OpenAI LLMを初期化
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            model="gpt-4o-mini",
            temperature=0.1
        )
        
        # ツールを初期化
        self.tools = [
            SearchProductsTool(),
            UpdateStockTool(),
            UpdateCategoryTool(),
            BulkUpdateStockTool(),
            ValidateProductTool(),
            GenerateHtmlTool(),
            PublishProductsTool(),
            UnpublishProductsTool()
        ]
        
        # ツールをLLMにバインド
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # ツールノードを作成
        self.tool_node = ToolNode(self.tools)
        
        # システムメッセージ
        self.system_message = """
あなたはECバックオフィス商品管理の専門アシスタントです。以下のワークフローに従って段階的に処理を進めてください：

## 処理ワークフロー：
1. **理解フェーズ**: ユーザーの要求を理解し、必要な操作を特定
2. **検索フェーズ**: 対象商品を検索・特定
3. **検証フェーズ**: 操作前の前提条件をチェック
4. **問題解決フェーズ**: 問題がある場合、解決方法を提示
5. **実行フェーズ**: 条件満足後、実際の操作を実行
6. **報告フェーズ**: 結果をユーザーに報告

## 商品棚上げの前提条件：
- ✅ 商品カテゴリーが設定されている
- ✅ 商品在庫が0より大きい

## 応答形式：
JSON形式で以下の情報を含めてください：
- message: ユーザー向けメッセージ
- action_type: 実行されたアクションタイプ
- html_content: 必要に応じてHTML内容
- next_actions: 推奨される次のアクション
- error: エラーがある場合のメッセージ

常に日本語で親しみやすく応答してください。
"""
        
        # LangGraphのワークフローを構築
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """LangGraphワークフローを構築"""
        
        # ワークフローグラフを作成
        workflow = StateGraph(AgentState)
        
        # ノードを追加
        workflow.add_node("understand_request", self._understand_request)
        workflow.add_node("search_products", self._search_products) 
        workflow.add_node("validate_conditions", self._validate_conditions)
        workflow.add_node("resolve_problems", self._resolve_problems)
        workflow.add_node("execute_action", self._execute_action)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("tools", self.tool_node)
        
        # エントリーポイントを設定
        workflow.set_entry_point("understand_request")
        
        # エッジを追加
        workflow.add_edge("understand_request", "search_products")
        workflow.add_edge("search_products", "validate_conditions")
        workflow.add_conditional_edges(
            "validate_conditions",
            self._decide_validation_result,
            {
                "problems_found": "resolve_problems",
                "ready_to_execute": "execute_action",
                "need_tools": "tools"
            }
        )
        workflow.add_edge("resolve_problems", "generate_response")
        workflow.add_edge("execute_action", "generate_response")
        workflow.add_edge("tools", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _get_langfuse_config(self, step_name: str = None, session_id: str = None, user_id: str = None) -> Dict:
        """Langfuse V3 CallbackHandlerの設定を取得"""
        if self.use_langfuse and self.langfuse_handler:
            # セッション/ユーザー固有のCallbackHandlerを作成
            if session_id or user_id:
                return {"callbacks": [self.langfuse_handler],
                        "metadata": {
                            "langfuse.user_id": user_id,
                            "langfuse.session_id": session_id,
                            "tags": [f"step:{step_name}", "langgraph", "product_management"] if step_name else ["langgraph", "product_management"]
                }}
            else:
                # デフォルトのCallbackHandlerを使用
                return {"callbacks": [self.langfuse_handler],
                        "metadata": {
                            "tags": [f"step:{step_name}", "langgraph", "product_management"] if step_name else ["langgraph", "product_management"]
                        }}
        return {}
    
    def _understand_request(self, state: AgentState) -> AgentState:
        """ユーザーリクエストを理解 (Langfuse V3 CallbackHandlerでLLM呼び出しをトレース)"""
        user_input = state["user_input"]
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        
        # リクエストの意図を分析
        analysis_prompt = f"""
ユーザーリクエスト: {user_input}

このリクエストを分析して、以下の情報を抽出してください：
1. 主要なアクション（検索、棚上げ、棚下げ、在庫更新、カテゴリー更新など）
2. 対象商品の特定条件（商品名、JANコード、カテゴリーなど）
3. 必要なパラメータ（在庫数、カテゴリー名など）

JSON形式で応答してください。
"""
        
        messages = [SystemMessage(content=analysis_prompt)]
        
        # Langfuse V3 CallbackHandlerを使用してLLM呼び出しをトレース
        config = self._get_langfuse_config("understand_request", session_id, user_id)
        response = self.llm.invoke(messages, config=config)
        
        # アクションタイプを特定
        action_type = self._extract_action_type(user_input)
        
        state["current_step"] = "understood"
        state["action_type"] = action_type
        state["intermediate_steps"].append({
            "step": "understand_request",
            "analysis": response.content,
            "action_type": action_type
        })
        
        return state
    
    def _search_products(self, state: AgentState) -> AgentState:
        """商品検索を実行"""
        user_input = state["user_input"]
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        
        # 検索ツールを使用
        search_tool = SearchProductsTool()
        
        try:
            # 自然言語から検索条件を抽出
            search_query = self._extract_search_conditions(user_input)
            
            # ツール実行（直接実行、上位のCallbackHandlerで追跡）
            search_result = search_tool._run(search_query)
            
            # 結果をパース
            if isinstance(search_result, str):
                try:
                    search_data = json.loads(search_result)
                    state["search_results"] = search_data.get("products", [])
                except json.JSONDecodeError:
                    state["search_results"] = []
                    state["error_message"] = "検索結果の解析に失敗しました"
            
            state["current_step"] = "searched"
            state["intermediate_steps"].append({
                "step": "search_products",
                "query": search_query,
                "results_count": len(state["search_results"] or [])
            })
            
        except Exception as e:
            state["error_message"] = f"商品検索中にエラーが発生しました: {str(e)}"
            state["search_results"] = []
        
        return state
    
    def _validate_conditions(self, state: AgentState) -> AgentState:
        """前提条件を検証（必要に応じてLLMを使用）"""
        action_type = state.get("action_type")
        search_results = state.get("search_results", [])
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        
        if not search_results:
            state["validation_results"] = {
                "valid": False,
                "issues": ["対象商品が見つかりません"]
            }
            state["current_step"] = "validation_failed"
            return state
        
        validation_issues = []
        
        # 棚上げの場合の特別な検証
        if action_type in ["publish", "棚上げ", "公開"]:
            validate_tool = ValidateProductTool()
            
            for product in search_results:
                jan_code = product.get("jan_code", "")
                if jan_code:
                    try:
                        validation_result = validate_tool._run(jan_code)
                        validation_data = json.loads(validation_result)
                        
                        if not validation_data.get("valid", False):
                            issues = validation_data.get("issues", [])
                            validation_issues.extend([f"商品{jan_code}: {issue}" for issue in issues])
                    except Exception as e:
                        validation_issues.append(f"商品{jan_code}の検証中にエラー: {str(e)}")
        
        # 複雑な検証の場合、LLMを使用してCallbackHandlerでトレース
        if validation_issues and action_type in ["publish", "棚上げ", "公開"]:
            validation_prompt = f"""
以下の商品検証で問題が見つかりました：
{json.dumps(validation_issues, ensure_ascii=False, indent=2)}

これらの問題を分析して、解決の優先順位と推奨アクションを提案してください。
"""
            messages = [SystemMessage(content=validation_prompt)]
            config = self._get_langfuse_config("validate_conditions_analysis", session_id, user_id)
            
            # LLM呼び出しをCallbackHandlerでトレース
            analysis_response = self.llm.invoke(messages, config=config)
            
            state["intermediate_steps"].append({
                "step": "validation_analysis",
                "llm_analysis": analysis_response.content
            })
        
        state["validation_results"] = {
            "valid": len(validation_issues) == 0,
            "issues": validation_issues
        }
        
        state["current_step"] = "validated"
        state["intermediate_steps"].append({
            "step": "validate_conditions",
            "validation_results": state["validation_results"]
        })
        
        return state
    
    def _resolve_problems(self, state: AgentState) -> AgentState:
        """問題解決画面を生成（LLMを使用して解決策を生成）"""
        validation_results = state.get("validation_results", {})
        issues = validation_results.get("issues", [])
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        
        # 問題に応じたHTML画面を生成
        html_tool = GenerateHtmlTool()
        
        try:
            # 問題の種類に応じて適切な画面タイプを決定
            page_type = "error_resolution"
            if any("カテゴリー" in issue for issue in issues):
                page_type = "category_form"
            elif any("在庫" in issue for issue in issues):
                page_type = "stock_form"
            
            # LLMを使用して問題解決提案を生成
            resolution_prompt = f"""
以下の商品管理問題に対する解決策を提案してください：
問題: {json.dumps(issues, ensure_ascii=False)}
画面タイプ: {page_type}

解決策として以下を含めてください：
1. 具体的な修正手順
2. ユーザーが実行すべきアクション
3. 注意事項

JSON形式で応答してください。
"""
            messages = [SystemMessage(content=resolution_prompt)]
            config = self._get_langfuse_config("problem_resolution", session_id, user_id)
            
            # LLM呼び出しをCallbackHandlerでトレース
            resolution_response = self.llm.invoke(messages, config=config)
            
            # HTML生成
            html_result = html_tool._run(page_type, {
                "issues": issues,
                "products": state.get("search_results", []),
                "resolution_advice": resolution_response.content
            })
            
            html_data = json.loads(html_result)
            if html_data.get("success"):
                state["html_content"] = html_data.get("html_content")
            
            state["intermediate_steps"].append({
                "step": "problem_resolution_llm",
                "resolution_advice": resolution_response.content
            })
            
        except Exception as e:
            state["error_message"] = f"問題解決画面の生成に失敗: {str(e)}"
        
        state["current_step"] = "problems_resolved"
        state["intermediate_steps"].append({
            "step": "resolve_problems",
            "issues_count": len(issues)
        })
        
        return state
    
    def _execute_action(self, state: AgentState) -> AgentState:
        """アクションを実行"""
        action_type = state.get("action_type")
        search_results = state.get("search_results", [])
        
        try:
            if action_type in ["publish", "棚上げ", "公開"]:
                publish_tool = PublishProductsTool()
                jan_codes = [p.get("jan_code") for p in search_results if p.get("jan_code")]
                result = publish_tool._run(",".join(jan_codes))
                
            elif action_type in ["unpublish", "棚下げ", "非公開"]:
                unpublish_tool = UnpublishProductsTool()
                jan_codes = [p.get("jan_code") for p in search_results if p.get("jan_code")]
                result = unpublish_tool._run(",".join(jan_codes))
                
            else:
                result = "アクションが特定できませんでした"
            
            state["current_step"] = "executed"
            state["intermediate_steps"].append({
                "step": "execute_action",
                "action_type": action_type,
                "result": result
            })
            
        except Exception as e:
            state["error_message"] = f"アクション実行中にエラー: {str(e)}"
        
        return state
    
    def _generate_response(self, state: AgentState) -> AgentState:
        """最終応答を生成（LLMを使用して最終メッセージを作成）"""
        current_step = state.get("current_step", "")
        error_message = state.get("error_message")
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        
        # LLMを使用して最終応答を生成
        response_prompt = f"""
以下の商品管理ワークフローが完了しました。ユーザーに対する親しみやすい最終メッセージを生成してください：

現在のステップ: {current_step}
エラーメッセージ: {error_message if error_message else "なし"}
実行されたステップ: {json.dumps(state.get("intermediate_steps", []), ensure_ascii=False)}

以下の要件でメッセージを作成してください：
1. 日本語で親しみやすい口調
2. 実行された操作の要約
3. 次にできることの提案

簡潔で分かりやすい応答をお願いします。
"""
        
        messages = [SystemMessage(content=response_prompt)]
        config = self._get_langfuse_config("generate_final_response", session_id, user_id)
        
        try:
            # LLM呼び出しをCallbackHandlerでトレース
            final_response = self.llm.invoke(messages, config=config)
            response_message = final_response.content
            
            state["intermediate_steps"].append({
                "step": "final_response_generation",
                "llm_generated_message": response_message
            })
            
        except Exception as e:
            # LLM生成に失敗した場合のフォールバック
            if error_message:
                response_message = f"申し訳ございません。{error_message}"
            elif current_step == "problems_resolved":
                response_message = "問題が見つかりました。解決方法を画面に表示しています。"
            elif current_step == "executed":
                response_message = "操作が正常に完了しました。"
            else:
                response_message = "処理を実行しました。"
        
        # 次のアクションを提案
        next_actions = self._suggest_next_actions(state)
        
        state["messages"].append(AIMessage(content=response_message))
        state["next_actions"] = next_actions
        state["current_step"] = "completed"
        
        return state
    
    def _decide_validation_result(self, state: AgentState) -> Literal["problems_found", "ready_to_execute", "need_tools"]:
        """検証結果に基づく次のステップを決定"""
        validation_results = state.get("validation_results", {})
        
        if not validation_results.get("valid", True):
            return "problems_found"
        else:
            return "ready_to_execute"
    
    def _extract_action_type(self, user_input: str) -> str:
        """ユーザー入力からアクションタイプを抽出"""
        user_input_lower = user_input.lower()
        
        if any(keyword in user_input_lower for keyword in ["棚上げ", "公開", "販売開始", "publish"]):
            return "publish"
        elif any(keyword in user_input_lower for keyword in ["棚下げ", "非公開", "販売停止", "unpublish"]):
            return "unpublish"
        elif any(keyword in user_input_lower for keyword in ["在庫", "stock"]):
            return "update_stock"
        elif any(keyword in user_input_lower for keyword in ["カテゴリー", "category"]):
            return "update_category"
        else:
            return "search"
    
    def _extract_search_conditions(self, user_input: str) -> str:
        """ユーザー入力から検索条件を抽出"""
        # 簡単な条件抽出ロジック
        if "在庫" in user_input and "未満" in user_input:
            return "low_stock"
        elif "コーヒー" in user_input:
            return "コーヒー"
        elif "JAN" in user_input or "jan" in user_input:
            # JANコードを抽出する簡単なロジック
            import re
            jan_match = re.search(r'(\d+)', user_input)
            if jan_match:
                return f"jan:{jan_match.group(1)}"
        
        return user_input
    
    def _suggest_next_actions(self, state: AgentState) -> List[str]:
        """次のアクションを提案"""
        current_step = state.get("current_step", "")
        action_type = state.get("action_type", "")
        
        if current_step == "problems_resolved":
            return ["問題を解決後、再度棚上げを実行", "他の商品を検索"]
        elif current_step == "executed":
            if action_type == "publish":
                return ["他の商品を棚上げ", "在庫状況を確認", "売上データを確認"]
            elif action_type == "unpublish":
                return ["他の商品を棚下げ", "商品情報を更新"]
        
        return ["他の商品を検索", "別の操作を実行"]

    @observe(name="product_management_workflow")
    def process_command(self, command: str, session_id: str = None, user_id: str = None) -> str:
        """LangGraphとLangfuse V3 CallbackHandlerを使用してコマンドを処理"""
        try:
            # 初期状態を設定
            initial_state = AgentState(
                messages=[HumanMessage(content=command)],
                current_step="start",
                user_input=command,
                search_results=None,
                validation_results=None,
                selected_products=None,
                action_type=None,
                html_content=None,
                error_message=None,
                next_actions=None,
                session_id=session_id,
                user_id=user_id,
                intermediate_steps=[]
            )
            
            # LangGraphワークフローを実行（CallbackHandlerが自動的にLLM呼び出しをトレース）
            config = self._get_langfuse_config("product_management_workflow", session_id, user_id)
            final_state = self.graph.invoke(initial_state, config=config)
            
            # 応答を構築
            response_data = {
                "message": final_state["messages"][-1].content if final_state["messages"] else "処理が完了しました",
                "action_type": final_state.get("action_type"),
                "html_content": final_state.get("html_content"),
                "next_actions": final_state.get("next_actions", []),
                "current_step": final_state.get("current_step"),
                "search_results_count": len(final_state.get("search_results") or []),
                "workflow_steps": len(final_state.get("intermediate_steps", [])),
                "langfuse_trace_available": self.use_langfuse
            }
            
            if final_state.get("error_message"):
                response_data["error"] = final_state["error_message"]
            
            output = json.dumps(response_data, ensure_ascii=False, indent=2)
            return output
            
        except Exception as e:
            error_msg = f"LangGraphワークフローでエラーが発生しました: {str(e)}"
            return json.dumps({
                "message": error_msg,
                "error": str(e)
            }, ensure_ascii=False)

    def get_workflow_visualization(self) -> str:
        """ワークフローの可視化情報を取得"""
        langfuse_status = "✅ Active (langfuse.langchain.CallbackHandler)" if self.use_langfuse else "❌ Disabled"
        return f"""
LangGraph + Langfuse V3 CallbackHandler 商品管理ワークフロー:
Langfuse Status: {langfuse_status}

1. understand_request (リクエスト理解) [LLM Call Traced]
   ↓
2. search_products (商品検索) [Tool Execution]
   ↓
3. validate_conditions (条件検証) [LLM Call Traced if complex]
   ↓
4. [条件分岐]
   ├─ problems_found → resolve_problems (問題解決) [LLM Call Traced]
   ├─ ready_to_execute → execute_action (アクション実行) [Tool Execution]
   └─ need_tools → tools (ツール実行)
   ↓
5. generate_response (応答生成) [LLM Call Traced]
   ↓
6. END

※ 全てのLLM呼び出しがLangfuse V3 CallbackHandlerによって自動的にトレースされます
※ セッションID、ユーザーIDによる追跡が可能です
※ ツール実行とワークフロー全体が階層的に記録されます
※ エラーハンドリングも含めて完全なトレーサビリティを実現
"""

    # def get_langfuse_status(self) -> Dict[str, Any]:
    #     """Langfuse V3の状態を取得"""
    #     status = {
    #         "available": LANGFUSE_AVAILABLE,
    #         "handler_initialized": self.langfuse_handler is not None,
    #         "callback_package": "langfuse.langchain.CallbackHandler",
    #         "environment_variables": {
    #             "LANGFUSE_PUBLIC_KEY": bool(os.getenv("LANGFUSE_PUBLIC_KEY")),
    #             "LANGFUSE_SECRET_KEY": bool(os.getenv("LANGFUSE_SECRET_KEY")),
    #             "LANGFUSE_HOST": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    #         }
    #     }
    #
    #     if LANGFUSE_AVAILABLE:
    #         try:
    #             import langfuse
    #             status["langfuse_version"] = langfuse.__version__
    #         except:
    #             status["langfuse_version"] = "unknown"
    #
    #     return status