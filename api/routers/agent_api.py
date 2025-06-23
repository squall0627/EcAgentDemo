from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_agents.product_management_agent import ProductManagementAgent, EXAMPLE_COMMANDS
from typing import Optional
import os
import json

router = APIRouter()

# グローバルエージェントインスタンス
agent_instance = None

def get_agent():
    global agent_instance
    if agent_instance is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="OpenAI APIキーが設定されていません")
        agent_instance = ProductManagementAgent(api_key)
    return agent_instance

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
    html_content: Optional[str] = None
    action_type: Optional[str] = None

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """EC商品管理エージェントとの対話 - HTML生成対応"""
    try:
        agent = get_agent()
        response = agent.process_command(request.message)
        
        # 応答がJSONの場合、HTML要素を抽出
        html_content = None
        action_type = None
        
        try:
            # 応答がJSON形式の場合をチェック
            if response.strip().startswith('{'):
                response_data = json.loads(response)
                html_content = response_data.get("html_content")
                action_type = response_data.get("action_type")
                
                # HTML生成が必要な場合の処理
                if response_data.get("generate_html"):
                    from ai_agents.tools.product_tools import GenerateHtmlTool
                    html_tool = GenerateHtmlTool()
                    html_result = html_tool._run(
                        response_data.get("page_type", "product_list"),
                        response_data.get("data", {})
                    )
                    html_data = json.loads(html_result)
                    if html_data.get("success"):
                        html_content = html_data.get("html_content")
                
                # ユーザー向けメッセージを取得
                response = response_data.get("message", response)
        except (json.JSONDecodeError, KeyError):
            # JSON形式でない場合はそのまま使用
            pass
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            html_content=html_content,
            action_type=action_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エージェント処理に失敗しました: {str(e)}")

@router.get("/examples")
async def get_example_commands():
    """サンプルコマンドを取得"""
    return {
        "examples": EXAMPLE_COMMANDS,
        "description": "EC商品管理エージェントと対話できるサンプルコマンドです"
    }

@router.get("/capabilities")
async def get_agent_capabilities():
    """エージェントの機能説明を取得"""
    return {
        "capabilities": [
            {
                "name": "商品検索",
                "description": "自然言語で商品を検索・フィルタリング",
                "examples": ["コーヒー商品を検索", "在庫が10未満の商品を検索"]
            },
            {
                "name": "商品棚上げ・棚下げ管理",
                "description": "商品の公開・非公開状態を管理（前提条件チェック付き）",
                "examples": ["商品を棚上げ", "コーヒー商品を全て棚下げ"]
            },
            {
                "name": "在庫管理",
                "description": "単一または複数商品の在庫レベル更新",
                "examples": ["JANコードxxxの在庫を50に設定", "在庫を一括更新"]
            },
            {
                "name": "カテゴリー管理",
                "description": "商品カテゴリーの設定または変更",
                "examples": ["商品カテゴリーを飲料に設定", "商品カテゴリーを変更"]
            },
            {
                "name": "動的HTML生成",
                "description": "操作に応じた管理画面を自動生成",
                "examples": ["商品リスト表示", "カテゴリー設定画面", "在庫管理画面"]
            },
            {
                "name": "エラー処理と誘導",
                "description": "問題解決まで段階的にサポート",
                "examples": ["棚上げ前提条件チェック", "エラー解決画面生成"]
            }
        ],
        "supported_languages": ["日本語", "英語", "中国語"],
        "natural_language": "自然言語での対話をサポート。特定のコマンド形式を覚える必要はありません",
        "workflow": [
            "1. 自然言語で商品検索",
            "2. 操作対象商品の確認",
            "3. 棚上げ前提条件の自動チェック",
            "4. 問題発見時は解決画面を自動生成",
            "5. 条件満足後、操作実行",
            "6. 結果の確認と次のアクション提案"
        ]
    }

@router.delete("/reset")
async def reset_agent_memory():
    """エージェントの対話メモリをリセット"""
    try:
        agent = get_agent()
        agent.memory.clear()
        return {"message": "エージェントのメモリがリセットされました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"リセットに失敗しました: {str(e)}")

@router.get("/status")
async def get_agent_status():
    """エージェントの状態確認"""
    try:
        global agent_instance
        is_initialized = agent_instance is not None
        
        status = {
            "initialized": is_initialized,
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "available_tools": [
                "search_products",
                "validate_product_status", 
                "publish_products",
                "unpublish_products",
                "update_stock",
                "update_category",
                "bulk_update_stock",
                "generate_html_page"
            ]
        }
        
        if is_initialized:
            status["memory_size"] = len(agent_instance.memory.chat_memory.messages)
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ステータス取得に失敗しました: {str(e)}")

@router.post("/execute-workflow")
async def execute_product_workflow(request: ChatRequest):
    """商品管理ワークフローの実行（検索→検証→処理→HTML生成）"""
    try:
        agent = get_agent()
        
        # ワークフロー実行
        workflow_response = agent.process_command(f"""
        以下のワークフローを実行してください：
        1. ユーザーリクエスト: {request.message}
        2. 適切な商品検索を実行
        3. 棚上げが必要な場合は前提条件を検証
        4. 問題がある場合は解決用HTML画面を生成
        5. 問題ない場合は操作を実行
        6. 結果をユーザーフレンドリーな形式で返却
        
        応答はJSON形式で以下を含めてください：
        - message: ユーザー向けメッセージ
        - action_type: 実行されたアクションタイプ
        - html_content: 必要に応じてHTML内容
        - next_actions: 推奨される次のアクション
        """)
        
        return ChatResponse(
            response=workflow_response,
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ワークフロー実行に失敗しました: {str(e)}")