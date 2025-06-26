import os
import json
from typing import TypedDict, Annotated, List, Dict, Any, Optional

from dotenv import load_dotenv
from langgraph.constants import START
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
from llm.llm_handler import LLMHandler
from utils.langfuse_handler import LangfuseHandler

load_dotenv()

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
        
        # LLMHandlerを使用してLLM管理を委譲
        self.llm_handler = LLMHandler(api_key, llm_type)
        
        # Langfuse V3 初期化 - LangfuseHandlerを使用
        self.langfuse_handler = LangfuseHandler(use_langfuse=use_langfuse)
        
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
        self.llm_with_tools = self.llm_handler.get_llm_with_tools(self.tools)
        self.tool_node = ToolNode(self.tools)
        
        # 柔軟なワークフローを構築
        self.graph = self._build_flexible_graph()

    def switch_llm(self, new_llm_type: str):
        """実行時にLLMタイプを切り替え"""
        self.llm_handler.switch_llm(new_llm_type)
        # ツール付きLLMも更新
        self.llm_with_tools = self.llm_handler.get_llm_with_tools(self.tools)

    def get_available_llms(self):
        """利用可能なLLMのリストを取得"""
        return self.llm_handler.get_available_llms()
    
    def get_llm_info(self, llm_type: str = None):
        """LLM情報を取得"""
        return self.llm_handler.get_llm_info(llm_type)

    @property
    def llm_type(self):
        """現在のLLMタイプを取得"""
        return self.llm_handler.get_current_llm_type()

    def assistant(self, state: AgentState):
        # システムメッセージ
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
        # 状態グラフを定義
        builder = StateGraph(AgentState)

        # ノードを定義：これらが実際の作業を行う
        builder.add_node("assistant", self.assistant)
        builder.add_node("tools", self.tool_node)

        # エッジを定義：これらが制御フローの移動方法を決定する
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant",
            # 最新のメッセージがツールを必要とする場合、ツールにルーティング
            # そうでなければ、直接応答を提供
            tools_condition,
        )
        builder.add_edge("tools", "assistant")
        
        return builder.compile()

    def process_command(self, command: str, llm_type: str = None, session_id: str = None, user_id: str = None) -> str:
        """ユーザーコマンドを処理 - 設定ベースの動的LLM切り替え対応"""
        
        # observeデコレータを取得（Langfuseが利用可能な場合のみ適用）
        observe_decorator = self.langfuse_handler.observe_decorator("product_management_workflow")
        
        @observe_decorator
        def _execute_workflow():
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
                config = self.langfuse_handler.get_config("product_management_workflow", session_id, user_id)
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
        
        return _execute_workflow()

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