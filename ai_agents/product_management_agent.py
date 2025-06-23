import os
import json
from typing import TypedDict, Annotated, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.constants import START
from typing_extensions import Literal
from langfuse import Langfuse
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from ai_agents.tools.product_tools import (
    # SearchProductsTool,
    UpdateStockTool,
    UpdateCategoryTool,
    BulkUpdateStockTool,
    ValidateProductTool,
    GenerateHtmlTool,
    PublishProductsTool,
    UnpublishProductsTool, search_products_tool
)

load_dotenv()

# Langfuse V3 インポート
LANGFUSE_AVAILABLE = False

try:
    from langfuse.langchain import CallbackHandler
    from langfuse import observe
    LANGFUSE_AVAILABLE = True
    print("✅ Langfuse V3 CallbackHandler正常にインポートされました")
except ImportError as e:
    print(f"❌ Langfuse V3 CallbackHandlerが利用できません: {e}")
    LANGFUSE_AVAILABLE = False

# LangGraph状態定義 - より柔軟な状態管理
class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | SystemMessage], add_messages]
    user_input: str
    # intent: Optional[str]  # ユーザー意図：検索、在庫更新、カテゴリー更新、棚上げ、棚下げなど
    # target_products: Optional[List[Dict]]  # 対象商品
    # action_params: Optional[Dict]  # アクションパラメータ（在庫数量、新カテゴリーなど）
    # execution_result: Optional[Dict]  # 実行結果
    html_content: Optional[str]
    error_message: Optional[str]
    next_actions: Optional[str]  # 次のステップ提案
    session_id: Optional[str]
    user_id: Optional[str]
    # workflow_path: List[str]  # 実行パスの記録

class ProductManagementAgent:
    def __init__(self, api_key: str, use_langfuse: bool = True):
        """柔軟な商品管理エージェント - 任意のノードから実行開始をサポート"""
        self.api_key = api_key
        self.use_langfuse = use_langfuse and LANGFUSE_AVAILABLE
        
        # Langfuse V3 初期化
        self.langfuse_handler = None
        if self.use_langfuse:
            try:
                public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
                secret_key = os.getenv("LANGFUSE_SECRET_KEY")
                host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
                if public_key and secret_key:
                    Langfuse(
                        public_key=public_key,
                        secret_key=secret_key,
                        host=host,
                    )
                    self.langfuse_handler = CallbackHandler()
                    print("✅ Langfuse V3が正常に初期化されました")
                else:
                    print("⚠️  Langfuse認証情報が見つかりません")
                    self.use_langfuse = False
            except Exception as e:
                print(f"❌ Langfuse初期化に失敗しました: {e}")
                self.use_langfuse = False

        # LLM初期化
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            model="gpt-4o-mini",
            temperature=0.1
        )

        # self.llm = ChatOllama(
        #     model="qwen2.5-coder:32b",  # or any other model you have installed in Ollama
        #     base_url="http://localhost:11434",  # Default Ollama URL
        #     temperature=0.7,
        # )
        
        # ツール初期化
        self.tools = [
            search_products_tool,
            UpdateStockTool(),
            UpdateCategoryTool(),
            BulkUpdateStockTool(),
            ValidateProductTool(),
            GenerateHtmlTool(),
            PublishProductsTool(),
            UnpublishProductsTool()
        ]
        
        # ツールマッピングを作成
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # ツール付きLLM
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.tool_node = ToolNode(self.tools)
        
        # 柔軟なワークフローを構築
        self.graph = self._build_flexible_graph()

    def assistant(self, state: AgentState):
        # System message
        sys_msg = SystemMessage(
            content="""
あなたはECバックオフィス商品管理の専門アシスタントです。管理者の自然言語コマンドを理解し、以下の機能を提供します：

## 主要機能：
1. **商品検索**: 自然言語で商品を検索・フィルタリング
2. **商品棚上げ・棚下げ管理**: 商品の棚上げ・棚下げ状態を管理
3. **商品在庫管理**: 商品の在庫状態を管理
4. **動的HTML生成**: 操作に応じた管理画面を自動生成
5. **エラー処理と誘導**: 問題解決まで段階的にサポート

## 商品棚上げの前提条件チェック：
商品を棚上げする前に、必ず以下の条件を確認してください：
- ✅ 商品カテゴリーが設定されている（null または空文字列ではない）
- ✅ 商品在庫が0より大きい

## HTML生成ルール：
- 商品リスト表示：検索結果を表形式で表示、各商品に操作ボタン付き
- カテゴリー設定画面：フォーム形式でカテゴリー選択・入力
- 在庫管理画面：数値入力フォームで在庫数量設定
- エラー画面：問題点を明示し、解決方法を提示

## 重要な動作原則：
1. ユーザーが問題解決まで段階的にサポート
2. 毎回応答の最後、***必ず***適切な操作画面(HTML)を自動生成

## 応答形式：
- JSON形式で構造化された応答
- HTML生成が必要な場合は "html_content" フィールドに含める
- エラーメッセージは "error" フィールドに日本語で記載
- 次のアクション提案は "next_actions" フィールドに含める

常に親しみやすく明確な日本語で応答し、管理者の業務効率向上を最優先に考えてください。
""")

        state["messages"].append(self.llm_with_tools.invoke([sys_msg] + state["messages"]))
        return state

    def _build_flexible_graph(self) -> StateGraph:
        """柔軟なワークフローグラフを構築"""
        # workflow = StateGraph(AgentState)
        #
        # # ノードを追加
        # workflow.add_node("intent_analysis", self._analyze_intent)  # 意図分析 - インテリジェントルーティング
        # workflow.add_node("direct_execution", self._direct_execution)  # 直接実行
        # workflow.add_node("search_first", self._search_first)  # まず検索してから実行
        # workflow.add_node("validate_and_execute", self._validate_and_execute)  # 検証後実行
        # workflow.add_node("generate_form", self._generate_form)  # フォーム生成
        # workflow.add_node("final_response", self._final_response)  # 最終レスポンス
        #
        # # エントリーポイント設定
        # workflow.set_entry_point("intent_analysis")
        #
        # # 条件エッジを追加 - 意図に基づくインテリジェントルーティング
        # workflow.add_conditional_edges(
        #     "intent_analysis",
        #     self._route_by_intent,
        #     {
        #         "direct_execution": "direct_execution",      # 直接実行（明確なパラメータあり）
        #         "search_first": "search_first",              # まず検索（商品を見つける必要あり）
        #         "validate_first": "validate_and_execute",    # 検証が必要（棚上げなど）
        #         "need_form": "generate_form",                # より多くの情報が必要
        #         "error": "final_response"                    # エラー処理
        #     }
        # )
        #
        # # すべてのパスは最終的にfinal_responseに
        # workflow.add_edge("direct_execution", "final_response")
        # workflow.add_edge("search_first", "final_response")
        # workflow.add_edge("validate_and_execute", "final_response")
        # workflow.add_edge("generate_form", "final_response")
        # workflow.add_edge("final_response", END)

        # Define the state graph
        # The graph
        builder = StateGraph(AgentState)

        # Define nodes: these do the work
        builder.add_node("assistant", self.assistant)
        builder.add_node("tools", self.tool_node)

        # Define edges: these determine how the control flow moves
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant",
            # If the latest message requires a tool, route to tools
            # Otherwise, provide a direct response
            tools_condition,
        )
        builder.add_edge("tools", "assistant")
        
        return builder.compile()
    
    def _get_langfuse_config(self, step_name: str = None, session_id: str = None, user_id: str = None) -> Dict:
        """Langfuse設定を取得"""
        if self.use_langfuse and self.langfuse_handler:
            return {"callbacks": [self.langfuse_handler],
                    "metadata": {
                        "langfuse.user_id": user_id,
                        "langfuse.session_id": session_id
                    }}
        return {}
    
    def _analyze_intent(self, state: AgentState) -> AgentState:
        """インテリジェント意図分析 - ワークフローパスを決定"""
        user_input = state["user_input"]
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        
        # インテリジェント意図分析プロンプトを構築
        intent_prompt = f"""
ユーザー入力: {user_input}

ユーザーの意図を分析し、重要な情報を抽出してください。JSON形式で返してください：

{{
    "intent": "検索|在庫更新|カテゴリー更新|棚上げ|棚下げ|一括操作",
    "execution_type": "direct|search_first|validate_first|need_form",
    "target_identification": {{
        "type": "jan_code|product_name|category|condition",
        "value": "具体的な値",
        "has_clear_target": true/false
    }},
    "action_params": {{
        "new_stock": 数量またはnull,
        "new_category": "カテゴリー名"またはnull,
        "quantity": 数量またはnull
    }},
    "confidence": 0.0-1.0
}}

execution_type説明：
- direct: 明確な商品識別子とパラメータがあり、直接実行可能
- search_first: まず商品を検索して見つける必要がある
- validate_first: 条件の検証が必要（棚上げ前のチェックなど）
- need_form: 必要なパラメータが不足、フォームが必要

例：
"JAN123456の在庫を50に変更" → direct (明確なJANコードと在庫値あり)
"コーヒー商品の在庫をすべて100に変更" → search_first (まずすべてのコーヒー商品を見つける必要)
"商品ABCを棚上げ" → validate_first (棚上げ条件をチェックする必要)
"商品在庫を修正" → need_form (具体的な商品と在庫値が不足)
"""
        
        messages = [SystemMessage(content=intent_prompt)]
        config = self._get_langfuse_config("intent_analysis", session_id, user_id)
        
        try:
            response = self.llm.invoke(messages, config=config)
            intent_data = json.loads(response.content)
            
            # 状態を更新
            state["intent"] = intent_data.get("intent")
            state["action_params"] = intent_data.get("action_params", {})
            state["workflow_path"] = ["intent_analysis"]
            
            # 直接実行タイプの場合、対象商品を抽出試行
            if intent_data.get("execution_type") == "direct":
                target_info = intent_data.get("target_identification", {})
                if target_info.get("has_clear_target"):
                    # 対象商品情報を構築
                    if target_info.get("type") == "jan_code":
                        state["target_products"] = [{"jan_code": target_info.get("value")}]
                    elif target_info.get("type") == "product_name":
                        state["target_products"] = [{"name": target_info.get("value")}]
            
            # 次のステップを設定
            state["next_step"] = intent_data.get("execution_type", "search_first")
            
        except Exception as e:
            state["error_message"] = f"意図分析に失敗しました: {str(e)}"
            state["next_step"] = "error"
        
        return state
    
    def _route_by_intent(self, state: AgentState) -> Literal["direct_execution", "search_first", "validate_first", "need_form", "error"]:
        """意図に基づくインテリジェントルーティング"""
        next_step = state.get("next_step", "search_first")
        
        if state.get("error_message"):
            return "error"
        elif next_step == "direct":
            return "direct_execution"
        elif next_step == "validate_first":
            return "validate_first"  
        elif next_step == "need_form":
            return "need_form"
        else:
            return "search_first"
    
    def _direct_execution(self, state: AgentState) -> AgentState:
        """直接実行 - 明確なパラメータがある場合に使用"""
        intent = state.get("intent")
        target_products = state.get("target_products", [])
        action_params = state.get("action_params", {})
        
        state["workflow_path"].append("direct_execution")
        
        try:
            if intent == "在庫更新" and target_products and action_params.get("new_stock") is not None:
                # 直接在庫更新
                tool = self.tool_map.get("update_stock")
                if tool and target_products[0].get("jan_code"):
                    result = tool._run(
                        f"{target_products[0]['jan_code']},{action_params['new_stock']}"
                    )
                    state["execution_result"] = {"success": True, "result": result}
                
            elif intent == "カテゴリー更新" and target_products and action_params.get("new_category"):
                # 直接カテゴリー更新
                tool = self.tool_map.get("update_category")
                if tool and target_products[0].get("jan_code"):
                    result = tool._run(
                        f"{target_products[0]['jan_code']},{action_params['new_category']}"
                    )
                    state["execution_result"] = {"success": True, "result": result}
                    
            else:
                state["error_message"] = "直接実行条件が満たされていません。より多くの情報が必要です"
                
        except Exception as e:
            state["error_message"] = f"直接実行に失敗しました: {str(e)}"
        
        return state
    
    def _search_first(self, state: AgentState) -> AgentState:
        """まず検索してから実行 - 対象商品を見つける必要がある場合に使用"""
        user_input = state["user_input"]
        intent = state.get("intent")
        action_params = state.get("action_params", {})
        
        state["workflow_path"].append("search_first")
        
        try:
            # 1. まず商品を検索
            search_tool = self.tool_map.get("search_products")
            search_query = self._extract_search_query(user_input)
            print(search_query)
            search_result = search_tool._run(search_query)
            
            if isinstance(search_result, str):
                search_data = json.loads(search_result)
                products = search_data.get("products", [])
                
                if not products:
                    state["error_message"] = "マッチする商品が見つかりませんでした"
                    return state
                
                state["target_products"] = products
                
                # 2. 意図に応じて相応の操作を実行
                if intent == "在庫更新" and action_params.get("new_stock") is not None:
                    # 一括在庫更新
                    tool = self.tool_map.get("bulk_update_stock") 
                    jan_codes = [p.get("jan_code") for p in products if p.get("jan_code")]
                    if jan_codes:
                        result = tool._run(f"{','.join(jan_codes)},{action_params['new_stock']}")
                        state["execution_result"] = {"success": True, "result": result, "affected_count": len(jan_codes)}
                
                elif intent == "棚上げ":
                    # 一括棚上げ
                    tool = self.tool_map.get("publish_products")
                    jan_codes = [p.get("jan_code") for p in products if p.get("jan_code")]
                    if jan_codes:
                        result = tool._run(",".join(jan_codes))
                        state["execution_result"] = {"success": True, "result": result, "affected_count": len(jan_codes)}
                
                elif intent == "棚下げ":
                    # 一括棚下げ  
                    tool = self.tool_map.get("unpublish_products")
                    jan_codes = [p.get("jan_code") for p in products if p.get("jan_code")]
                    if jan_codes:
                        result = tool._run(",".join(jan_codes))
                        state["execution_result"] = {"success": True, "result": result, "affected_count": len(jan_codes)}
                
                else:
                    # 検索のみ、操作は実行しない
                    state["execution_result"] = {
                        "success": True, 
                        "result": f"{len(products)}個の商品が見つかりました", 
                        "products": products
                    }
        
        except Exception as e:
            state["error_message"] = f"検索実行に失敗しました: {str(e)}"
        
        return state
    
    def _validate_and_execute(self, state: AgentState) -> AgentState:
        """検証後実行 - 前提条件をチェックする必要がある場合に使用"""
        target_products = state.get("target_products", [])
        intent = state.get("intent")
        
        state["workflow_path"].append("validate_and_execute")
        
        try:
            # 対象商品がない場合、まず検索
            if not target_products:
                search_tool = self.tool_map.get("search_products")
                search_query = self._extract_search_query(state["user_input"])
                search_result = search_tool._run(search_query)
                
                if isinstance(search_result, str):
                    search_data = json.loads(search_result)
                    target_products = search_data.get("products", [])
                    state["target_products"] = target_products
            
            if not target_products:
                state["error_message"] = "対象商品が見つかりませんでした"
                return state
            
            # 検証して実行
            if intent == "棚上げ":
                validate_tool = self.tool_map.get("validate_product")
                publish_tool = self.tool_map.get("publish_products")
                
                valid_products = []
                issues = []
                
                # 一つずつ検証
                for product in target_products:
                    jan_code = product.get("jan_code")
                    if jan_code:
                        validation_result = validate_tool._run(jan_code)
                        validation_data = json.loads(validation_result)
                        
                        if validation_data.get("valid"):
                            valid_products.append(product)
                        else:
                            issues.extend(validation_data.get("issues", []))
                
                if valid_products:
                    # 棚上げを実行
                    jan_codes = [p.get("jan_code") for p in valid_products]
                    result = publish_tool._run(",".join(jan_codes))
                    
                    state["execution_result"] = {
                        "success": True,
                        "result": result,
                        "valid_count": len(valid_products),
                        "issues": issues
                    }
                else:
                    state["error_message"] = f"すべての商品に問題があります: {'; '.join(issues)}"
        
        except Exception as e:
            state["error_message"] = f"検証実行に失敗しました: {str(e)}"
        
        return state
    
    def _generate_form(self, state: AgentState) -> AgentState:
        """フォーム生成 - より多くの情報が必要な場合に使用"""
        intent = state.get("intent")
        
        state["workflow_path"].append("generate_form")
        
        try:
            html_tool = self.tool_map.get("generate_html")
            
            if intent == "在庫更新":
                form_type = "stock_form"
            elif intent == "カテゴリー更新":
                form_type = "category_form"
            else:
                form_type = "general_form"
            
            html_result = html_tool._run(form_type, {
                "intent": intent,
                "message": "操作を完了するためにより多くの情報を提供してください"
            })
            
            html_data = json.loads(html_result)
            if html_data.get("success"):
                state["html_content"] = html_data.get("html_content")
                state["execution_result"] = {"success": True, "needs_more_info": True}
        
        except Exception as e:
            state["error_message"] = f"フォーム生成に失敗しました: {str(e)}"
        
        return state
    
    def _final_response(self, state: AgentState) -> AgentState:
        """最終レスポンスを生成"""
        intent = state.get("intent")
        execution_result = state.get("execution_result", {})
        error_message = state.get("error_message")
        workflow_path = state.get("workflow_path", [])
        
        # レスポンスメッセージを構築
        if error_message:
            response_message = f"申し訳ございません。{error_message}"
        elif execution_result.get("success"):
            if execution_result.get("needs_more_info"):
                response_message = "操作を完了するために追加情報が必要です。フォームにご入力ください。"
            elif execution_result.get("affected_count"):
                response_message = f"操作が完了しました。{execution_result['affected_count']}個の商品に適用されました。"
            else:
                response_message = "操作が正常に完了しました。"
        else:
            response_message = "処理を実行しました。"
        
        # 実行パス情報を追加
        response_message += f"\n実行パス: {' → '.join(workflow_path)}"
        
        state["messages"].append(AIMessage(content=response_message))
        
        return state
    
    def _extract_search_query(self, user_input: str) -> str:
        """ユーザー入力から検索クエリを抽出"""
        # シンプルなクエリ抽出ロジック
        if "コーヒー" in user_input:
            return "コーヒー"
        elif "在庫" in user_input and "未満" in user_input:
            return "low_stock"
        elif "JAN" in user_input or "jan" in user_input:
            import re
            jan_match = re.search(r'(\d+)', user_input)
            if jan_match:
                return f"jan:{jan_match.group(1)}"
        
        return user_input

    @observe(name="product_management_workflow")
    def process_command(self, command: str, session_id: str = None, user_id: str = None) -> str:
        """ユーザーコマンドを処理 - 柔軟なワークフロー"""
        try:
            # Langfuseコンテキストを設定
            # if self.use_langfuse and langfuse_context:
            #     langfuse_context.update_current_trace(
            #         metadata={
            #             "agent_type": "flexible_product_management",
            #             "command": command
            #         },
            #         session_id=session_id,
            #         user_id=user_id
            #     )
            
            # 初期状態
            initial_state = AgentState(
                messages=[HumanMessage(content=command)],
                user_input=command,
                # intent=None,
                # target_products=None,
                # action_params=None,
                # execution_result=None,
                html_content=None,
                error_message=None,
                next_actions=None,
                session_id=session_id,
                user_id=user_id,
                # workflow_path=[]
            )
            
            # 柔軟なワークフローを実行
            config = self._get_langfuse_config("product_management_workflow", session_id, user_id)
            final_state = self.graph.invoke(initial_state, config=config)
            
            # レスポンスを構築
            response_data = {
                "message": final_state["messages"][-1].content if final_state["messages"] else "処理が完了しました",
                # "intent": final_state.get("intent"),
                # "execution_result": final_state.get("execution_result"),
                "html_content": final_state.get("html_content"),
                "next_actions": final_state.get("next_actions"),
                # "workflow_path": final_state.get("workflow_path", []),
                # "target_products_count": len(final_state.get("target_products") or []),
                # "langfuse_trace_id": langfuse_context.get_current_trace_id() if self.use_langfuse and langfuse_context else None
            }
            
            if final_state.get("error_message"):
                response_data["error"] = final_state["error_message"]
            
            return json.dumps(response_data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_msg = f"柔軟なワークフロー実行に失敗しました: {str(e)}"
            return json.dumps({
                "message": error_msg,
                "error": str(e)
            }, ensure_ascii=False)

    def get_workflow_info(self) -> str:
        """ワークフロー情報を取得"""
        return """
柔軟な商品管理LangGraphワークフロー:

エントリーポイント: intent_analysis (インテリジェント意図分析)
├─ ユーザー入力を分析し、意図とパラメータを抽出
├─ インテリジェントに実行パスを決定

ルーティング選択:
├─ direct_execution (直接実行)
│  └─ 条件: 明確な商品識別子 + 完全なパラメータ
│  └─ 例: "JAN123456の在庫を50に変更"
│
├─ search_first (まず検索してから実行)  
│  └─ 条件: 対象商品を検索して見つける必要がある
│  └─ 例: "すべてのコーヒー商品の在庫を100に変更"
│
├─ validate_and_execute (検証後実行)
│  └─ 条件: 前提条件の検証が必要
│  └─ 例: "商品ABCを棚上げ"
│
└─ generate_form (フォーム生成)
   └─ 条件: 必要なパラメータが不足
   └─ 例: "商品在庫を修正"

利点:
✅ インテリジェントルーティング - LLMが自動的に最適な実行パスを選択
✅ 柔軟な開始点 - 任意のノードから開始可能
✅ パラメータ抽出 - ユーザー意図とパラメータを自動解析
✅ エラー処理 - 優雅な降格とエラー回復
✅ 完全な追跡 - Langfuseによる全プロセス記録
"""

# 使用例とテストケース
EXAMPLE_COMMANDS = [
    # 直接実行タイプ
    "JAN123456789の在庫を50に変更",
    "商品987654321のカテゴリーを飲料に変更",
    
    # 検索後実行タイプ  
    "すべてのコーヒー商品の在庫を100に変更",
    "在庫不足の商品をすべて棚下げ",
    "飲料カテゴリーの商品をすべて棚上げ",
    
    # 検証後実行タイプ
    "商品ABC123を棚上げ",
    "JAN555666777を販売開始",
    
    # フォームが必要なタイプ
    "商品在庫を修正",
    "商品情報を更新",
    "商品管理"
]

if __name__ == "__main__":
    # 初期状態
    initial_state = AgentState(
        messages=[HumanMessage(content="JAN code 1000000000001の商品を検索し、かつ商品詳細一覧画面を生成してください。")],
        user_input="JAN code 1000000000001の商品を検索し、かつ商品詳細一覧画面を生成してください。",
        # intent=None,
        # target_products=None,
        # action_params=None,
        # execution_result=None,
        html_content=None,
        error_message=None,
        next_actions=None,
        session_id=None,
        user_id=None,
        # workflow_path=[]
    )

    api_key = os.getenv("OPENAI_API_KEY")

    agent_instance = ProductManagementAgent(api_key)
    # 柔軟なワークフローを実行
    config = agent_instance._get_langfuse_config("product_management_workflow")
    final_state = agent_instance.graph.invoke(initial_state, config=config)
    print(final_state)