import os
import json
from typing import TypedDict, Annotated, List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.constants import START
from langfuse import Langfuse
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from ai_agents.tools.product_tools import (
    UpdateStockTool,
    UpdatePriceTool,
    UpdateDescriptionTool,
    UpdateCategoryTool,
    BulkUpdateStockTool,
    BulkUpdatePriceTool,
    ValidateCanPublishProductTool,
    GenerateHtmlTool,
    PublishProductsTool,
    UnpublishProductsTool, 
    search_products_tool
)
from config.llm_config_loader import llm_config

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
    html_content: Optional[str]
    error_message: Optional[str]
    next_actions: Optional[str]
    session_id: Optional[str]
    user_id: Optional[str]

class ProductManagementAgent:
    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """柔軟な商品管理エージェント - 設定ファイルベースの動的LLM選択"""
        self.api_key = api_key
        self.llm_type = llm_type or llm_config.get_default_model()
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

        # 動的LLM初期化
        self.llm = self._initialize_llm()
        
        # ツール初期化
        self.tools = [
            search_products_tool,
            UpdateStockTool(),
            UpdatePriceTool(),
            UpdateDescriptionTool(),
            UpdateCategoryTool(),
            BulkUpdateStockTool(),
            BulkUpdatePriceTool(),
            ValidateCanPublishProductTool(),
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

    def _initialize_llm(self):
        """設定ファイルに基づいてLLMを初期化"""
        # モデル利用可能性を検証
        is_available, message = llm_config.validate_model_availability(self.llm_type)
        if not is_available:
            print(f"⚠️ {message}")
            # フォールバックモデルを使用
            self.llm_type = llm_config.get_default_model()
            print(f"🔄 フォールバックモデル {self.llm_type} を使用します")
        
        model_config = llm_config.get_model_config(self.llm_type)
        if not model_config:
            raise ValueError(f"モデル設定が見つかりません: {self.llm_type}")
        
        provider = model_config["provider"]
        model_name = model_config["model"]
        temperature = model_config.get("temperature", 0.7)
        
        try:
            if provider == "ollama":
                print(f"🦙 Ollama LLM ({model_name}) を初期化中...")
                return ChatOllama(
                    model=model_name,
                    base_url=model_config.get("base_url", "http://localhost:11434"),
                    temperature=temperature,
                )
            elif provider == "openai":
                print(f"🤖 OpenAI LLM ({model_name}) を初期化中...")
                return ChatOpenAI(
                    openai_api_key=self.api_key,
                    model=model_name,
                    temperature=temperature
                )
            elif provider == "anthropic":
                print(f"🧠 Anthropic LLM ({model_name}) を初期化中...")
                try:
                    from langchain_anthropic import ChatAnthropic
                    return ChatAnthropic(
                        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                        model=model_name,
                        temperature=temperature
                    )
                except ImportError:
                    print("❌ langchain_anthropicがインストールされていません")
                    return self._fallback_to_default()
            else:
                print(f"❌ 未対応のプロバイダー: {provider}")
                return self._fallback_to_default()
                
        except Exception as e:
            print(f"❌ LLM初期化に失敗しました: {e}")
            return self._fallback_to_default()

    def _fallback_to_default(self):
        """デフォルトモデルにフォールバック"""
        default_model = llm_config.get_default_model()
        default_config = llm_config.get_model_config(default_model)
        
        print(f"🔄 デフォルトモデル {default_model} にフォールバックします")
        
        if default_config["provider"] == "ollama":
            return ChatOllama(
                model=default_config["model"],
                base_url=default_config.get("base_url", "http://localhost:11434"),
                temperature=default_config.get("temperature", 0.7),
            )
        else:
            # 最後の手段としてOpenAI
            return ChatOpenAI(
                openai_api_key=self.api_key,
                model="gpt-4o-mini",
                temperature=0.1
            )

    def switch_llm(self, new_llm_type: str):
        """実行時にLLMタイプを切り替え"""
        if new_llm_type != self.llm_type:
            old_type = self.llm_type
            self.llm_type = new_llm_type
            self.llm = self._initialize_llm()
            self.llm_with_tools = self.llm.bind_tools(self.tools)
            
            new_config = llm_config.get_model_config(new_llm_type)
            if new_config:
                print(f"✅ LLMを{old_type}から{new_config['provider']}:{new_config['model']}に切り替えました")
            else:
                print(f"✅ LLMを{new_llm_type}に切り替えました")

    def get_available_llms(self):
        """利用可能なLLMのリストを取得"""
        return [model["value"] for model in llm_config.get_all_models()]
    
    def get_llm_info(self, llm_type: str = None):
        """LLM情報を取得"""
        target_type = llm_type or self.llm_type
        model_config = llm_config.get_model_config(target_type)
        
        if model_config:
            return {
                "type": target_type,
                "provider": model_config.get("provider", "unknown"),
                "model": model_config.get("model", "unknown"),
                "temperature": model_config.get("temperature", 0.7),
                "label": model_config.get("label", target_type),
                "description": model_config.get("description", "")
            }
        else:
            return {
                "type": target_type,
                "provider": "unknown",
                "model": "unknown",
                "temperature": 0.7,
                "label": target_type,
                "description": "設定が見つかりません"
            }

    def assistant(self, state: AgentState):
        # System message
        sys_msg = SystemMessage(
            content="""
あなたはECバックオフィス商品管理の専門アシスタントです。管理者の自然言語コマンドを理解し、以下の機能を提供します：

## 主要機能：
1. **商品検索**: 自然言語で商品を検索・フィルタリング
2. **商品棚上げ・棚下げ管理**: 商品の棚上げ・棚下げ状態を管理
3. **商品在庫管理**: 商品の在庫状態を管理
4. **商品価格管理**: 商品の価格設定・更新を管理（個別・一括対応）
5. **商品説明管理**: 商品の説明文を管理・更新
6. **動的HTML生成**: 操作に応じた管理画面を自動生成
7. **エラー処理と誘導**: 問題解決まで段階的にサポート

## 商品棚上げの前提条件チェック：
商品を棚上げする前に、必ず以下の条件を確認してください：
- ✅ 商品カテゴリーが設定されている（null または空文字列ではない）
- ✅ 商品在庫が0より大きい
- ✅ 商品価格が設定されている（0より大きい）

## HTML生成ルール：
- 商品リスト表示：検索結果を表形式で表示、各商品に操作ボタン付き
- カテゴリー設定画面：フォーム形式でカテゴリー選択・入力
- 在庫管理画面：数値入力フォームで在庫数量設定
- 価格管理画面：数値入力フォームで価格設定（通貨表示対応）
- 商品説明管理画面：テキストエリアで説明文編集
- エラー画面：問題点を明示し、解決方法を提示

## 価格に関する注意事項：
- 価格は必ず0以上の値を設定してください
- 価格表示は通貨形式（¥1,234.56）で表示
- 一括価格更新では、無効な価格値をスキップして処理続行

## 重要な動作原則：
1. ユーザーが問題解決まで段階的にサポート
2. 毎回応答の最後、***必ず***適切な操作画面(HTML)を自動生成

## 応答形式：
- JSON形式で構造化された応答
- HTML生成が必要な場合は "html_content" フィールドに含め、直接に画面にレンダリングしてください
- エラーメッセージは "error" フィールドに日本語で記載
- 次のアクション提案は "next_actions" フィールドに含める

常に親しみやすく明確な日本語で応答し、管理者の業務効率向上を最優先に考えてください。
""")

        state["messages"].append(self.llm_with_tools.invoke([sys_msg] + state["messages"]))
        return state

    def _build_flexible_graph(self) -> StateGraph:
        """柔軟なワークフローグラフを構築"""
        # Define the state graph
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

    @observe(name="product_management_workflow")
    def process_command(self, command: str, llm_type: str = None, session_id: str = None, user_id: str = None) -> str:
        """ユーザーコマンドを処理 - 設定ベースの動的LLM切り替え対応"""
        try:
            # LLMタイプが指定された場合は切り替え
            if llm_type and llm_type != self.llm_type:
                self.switch_llm(llm_type)
            
            # 初期状態
            initial_state = AgentState(
                messages=[HumanMessage(content=command)],
                user_input=command,
                html_content=None,
                error_message=None,
                next_actions=None,
                session_id=session_id,
                user_id=user_id,
            )
            
            # 柔軟なワークフローを実行
            config = self._get_langfuse_config("product_management_workflow", session_id, user_id)
            final_state = self.graph.invoke(initial_state, config=config)
            
            # レスポンスを構築
            response_data = {
                "message": final_state["messages"][-1].content if final_state["messages"] else "処理が完了しました",
                "html_content": final_state.get("html_content"),
                "next_actions": final_state.get("next_actions"),
                "llm_type_used": self.llm_type,
                "llm_info": self.get_llm_info()
            }
            
            if final_state.get("error_message"):
                response_data["error"] = final_state["error_message"]
            
            return json.dumps(response_data, ensure_ascii=False, indent=2)
            
        except Exception as e:
            error_msg = f"ワークフロー実行に失敗しました: {str(e)}"
            return json.dumps({
                "message": error_msg,
                "error": str(e),
                "llm_type_used": self.llm_type,
                "llm_info": self.get_llm_info()
            }, ensure_ascii=False)

# 使用例とテストケース
EXAMPLE_COMMANDS = [
    # 直接実行タイプ
    "JAN123456789の在庫を50に変更",
    "商品987654321のカテゴリーを飲料に変更",
    "JAN123456789の価格を1500円に設定",
    "商品987654321の商品説明を更新",

    # 検索後実行タイプ
    "すべてのコーヒー商品の在庫を100に変更",
    "在庫不足の商品をすべて棚下げ",
    "飲料カテゴリーの商品をすべて棚上げ",
    "価格が1000円以下の商品を検索",
    "説明文に「限定」を含む商品を検索",

    # 検証後実行タイプ
    "商品ABC123を棚上げ",
    "JAN555666777を販売開始",

    # フォームが必要なタイプ
    "商品在庫を修正",
    "商品情報を更新",
    "商品管理",
    "商品価格を設定",
    "商品説明を編集"
]

# 使用例
if __name__ == "__main__":
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 設定ベースでエージェントを初期化
    agent = ProductManagementAgent(api_key)
    
    # 利用可能なLLMを表示
    print("利用可能なLLM:", agent.get_available_llms())
    
    # テスト実行
    result = agent.process_command("JAN code 1000000000001の商品を検索し、商品詳細一覧画面を生成してください。")
    print(result)