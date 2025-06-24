from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ai_agents.product_management_agent import ProductManagementAgent, EXAMPLE_COMMANDS
from typing import Optional
import os
import json
from config.llm_config_loader import llm_config

router = APIRouter()

# グローバルエージェントインスタンス
agent_instance = None

def get_agent(llm_type: str = None):
    """設定ファイルベースでエージェントインスタンスを取得または作成"""
    global agent_instance
    
    # デフォルトモデルを設定
    if not llm_type:
        llm_type = llm_config.get_default_model()
    
    # モデル利用可能性をチェック
    is_available, message = llm_config.validate_model_availability(llm_type)
    if not is_available:
        print(f"⚠️ {message}")
        # フォールバックモデルを使用
        llm_type = llm_config.get_default_model()
    
    # エージェントが存在しない、または異なるLLMタイプの場合は再作成
    if agent_instance is None or agent_instance.llm_type != llm_type:
        api_key = os.getenv("OPENAI_API_KEY")
        
        # 新しいエージェントインスタンスを作成
        agent_instance = ProductManagementAgent(api_key, llm_type=llm_type)
        print(f"🔄 エージェントを{llm_type}で初期化しました")
    
    return agent_instance

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    llm_type: Optional[str] = "ollama"

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
    html_content: Optional[str] = None
    action_type: Optional[str] = None
    workflow_step: Optional[str] = None
    llm_type_used: Optional[str] = None  # 実際に使用されたLLMタイプを返す

async def chat_with_agent(request: ChatRequest):
    """LangGraph商品管理エージェントとの対話"""
    try:
        # リクエストからllm_typeを取得（デフォルトはollama）
        llm_type = getattr(request, 'llm_type', 'ollama')
        
        # llm_typeに基づいてエージェントを取得
        agent = get_agent(llm_type)
        
        # コマンドを処理（llm_typeも渡す）
        response = agent.process_command(
            request.message, 
            llm_type=llm_type,
            session_id=request.session_id
        )
        
        # 応答がJSONの場合、情報を抽出
        html_content = None
        action_type = None
        workflow_step = None
        llm_type_used = llm_type
        
        try:
            if response.strip().startswith('{'):
                response_data = json.loads(response)
                html_content = response_data.get("html_content")
                action_type = response_data.get("action_type")
                workflow_step = response_data.get("current_step")
                llm_type_used = response_data.get("llm_type_used", llm_type)
                
                # ユーザー向けメッセージを取得
                response = response_data.get("message", response)
        except (json.JSONDecodeError, KeyError):
            pass
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            html_content=html_content,
            action_type=action_type,
            workflow_step=workflow_step,
            llm_type_used=llm_type_used  # 使用されたLLMタイプを返す
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LangGraphエージェント処理に失敗しました: {str(e)}")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent_endpoint(request: ChatRequest):
    return await chat_with_agent(request)

@router.get("/examples")
async def get_example_commands():
    """サンプルコマンドを取得"""
    return {
        "examples": EXAMPLE_COMMANDS,
        "description": "LangGraph EC商品管理エージェントと対話できるサンプルコマンドです"
    }

@router.get("/workflow")
async def get_workflow_info():
    """LangGraphワークフロー情報を取得"""
    try:
        agent = get_agent()
        return {
            "workflow_type": "LangGraph",
            "visualization": agent.get_workflow_visualization(),
            "steps": [
                {
                    "name": "understand_request",
                    "description": "ユーザーリクエストの理解と意図分析"
                },
                {
                    "name": "search_products", 
                    "description": "対象商品の検索と特定"
                },
                {
                    "name": "validate_conditions",
                    "description": "操作前の前提条件検証"
                },
                {
                    "name": "resolve_problems",
                    "description": "問題がある場合の解決方法提示"
                },
                {
                    "name": "execute_action",
                    "description": "実際の操作実行"
                },
                {
                    "name": "generate_response",
                    "description": "最終応答の生成"
                }
            ],
            "advantages": [
                "明確なワークフロー制御",
                "段階的な状態管理",
                "条件分岐による柔軟な処理",
                "エラーハンドリングの改善",
                "トレーサビリティの向上"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ワークフロー情報取得に失敗: {str(e)}")

@router.get("/capabilities")
async def get_agent_capabilities():
    """エージェントの機能説明を取得"""
    return {
        "agent_type": "LangGraph商品管理エージェント",
        "capabilities": [
            {
                "name": "段階的商品検索",
                "description": "自然言語リクエストから商品を段階的に検索・特定",
                "examples": ["コーヒー商品を検索", "在庫が10未満の商品を検索"]
            },
            {
                "name": "条件付き棚上げ・棚下げ",
                "description": "前提条件を自動チェックして商品の公開・非公開を管理",
                "examples": ["商品を棚上げ", "コーヒー商品を全て棚下げ"]
            },
            {
                "name": "問題解決ワークフロー",
                "description": "問題発見時に自動的に解決方法を提示",
                "examples": ["カテゴリー未設定商品の解決", "在庫不足商品の解決"]
            },
            {
                "name": "状態管理とトレーサビリティ",
                "description": "各処理ステップの状態を管理し、全プロセスを追跡可能",
                "examples": ["処理フローの可視化", "エラー原因の特定"]
            }
        ],
        "workflow_features": [
            "リクエスト理解 → 商品検索 → 条件検証 → 問題解決/実行 → 応答生成",
            "各ステップでの状態保持",
            "条件分岐による柔軟な処理フロー",
            "エラー時の自動回復処理"
        ]
    }

@router.delete("/reset")
async def reset_agent():
    """エージェントのリセット（LangGraphは状態を持たないため、インスタンスを再作成）"""
    try:
        global agent_instance
        agent_instance = None
        return {"message": "LangGraphエージェントがリセットされました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"リセットに失敗しました: {str(e)}")

@router.get("/status")
async def get_agent_status():
    """エージェントの状態確認"""
    try:
        global agent_instance
        is_initialized = agent_instance is not None
        
        status = {
            "agent_type": "LangGraph商品管理エージェント",
            "initialized": is_initialized,
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
            "langfuse_available": agent_instance.use_langfuse if is_initialized else False,
            "workflow_nodes": [
                "understand_request",
                "search_products", 
                "validate_conditions",
                "resolve_problems",
                "execute_action",
                "generate_response",
                "tools"
            ],
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
        
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ステータス取得に失敗しました: {str(e)}")

@router.post("/execute-workflow")
async def execute_product_workflow(request: ChatRequest):
    """LangGraph商品管理ワークフローの段階的実行"""
    try:
        agent = get_agent()
        
        # LangGraphワークフローは自動的に段階実行される
        response = agent.process_command(request.message, session_id=request.session_id)
        
        return ChatResponse(
            response=response,
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LangGraphワークフロー実行に失敗しました: {str(e)}")