from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import SystemMessage
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

class ProductManagementAgent:
    def __init__(self, api_key: str):
        """商品管理エージェントを初期化"""
        self.api_key = api_key
        
        # OpenAI LLMを初期化
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            model="gpt-3.5-turbo",
            temperature=0.1
        )
        
        # メモリを初期化
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
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
        
        # システムメッセージを設定
        self.system_message = SystemMessage(content="""
あなたはECバックオフィス商品管理の専門アシスタントです。管理者の自然言語コマンドを理解し、以下の機能を提供します：

## 主要機能：
1. **商品検索**: 自然言語で商品を検索・フィルタリング
2. **商品棚上げ・棚下げ管理**: 商品の公開・非公開状態を管理
3. **動的HTML生成**: 操作に応じた管理画面を自動生成
4. **エラー処理と誘導**: 問題解決まで段階的にサポート

## 商品棚上げの前提条件チェック：
商品を棚上げする前に、必ず以下の条件を確認してください：
- ✅ 商品カテゴリーが設定されている（null または空文字列ではない）
- ✅ 商品在庫が0より大きい

## 操作フロー：
1. **検索フェーズ**: ユーザーの自然言語で商品を検索
2. **状態確認フェーズ**: 棚上げ前提条件をチェック
3. **問題解決フェーズ**: 条件未満の場合、適切な操作画面を生成
4. **実行フェーズ**: 条件満足後、棚上げ処理を実行

## キーワード対応：
- "検索"、"探す"、"見つける" → search_products
- "棚上げ"、"公開"、"販売開始" → publish_products (前提条件チェック付き)
- "棚下げ"、"非公開"、"販売停止" → unpublish_products
- "カテゴリー設定" → update_category + generate_category_form
- "在庫補充"、"在庫追加" → update_stock + generate_stock_form
- "確認"、"チェック" → validate_product_status

## HTML生成ルール：
- 商品リスト表示：検索結果を表形式で表示、各商品に操作ボタン付き
- カテゴリー設定画面：フォーム形式でカテゴリー選択・入力
- 在庫管理画面：数値入力フォームで在庫数量設定
- エラー画面：問題点を明示し、解決方法を提示

## 重要な動作原則：
1. 必ず商品を検索して存在確認後に操作実行
2. 棚上げ前の前提条件チェックは必須
3. 条件未満の場合、適切な操作画面を自動生成
4. ユーザーが問題解決まで段階的にサポート
5. 最終的に棚上げ成功まで誘導

## 応答形式：
- JSON形式で構造化された応答
- HTML生成が必要な場合は "html_content" フィールドに含める
- エラーメッセージは "error" フィールドに日本語で記載
- 次のアクション提案は "next_actions" フィールドに含める

常に親しみやすく明確な日本語で応答し、管理者の業務効率向上を最優先に考えてください。
""")
        
        # プロンプトテンプレートを作成
        prompt = ChatPromptTemplate.from_messages([
            self.system_message,
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # エージェントを作成
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # エージェント実行器を作成
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            return_intermediate_steps=True
        )

    def process_command(self, command: str) -> str:
        """自然言語コマンドを処理"""
        try:
            response = self.agent_executor.invoke({"input": command})
            return response["output"]
        except Exception as e:
            return f"エラーが発生しました: {str(e)}"

    def get_conversation_history(self) -> list:
        """対話履歴を取得"""
        return self.memory.chat_memory.messages