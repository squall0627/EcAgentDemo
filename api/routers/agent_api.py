from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from ai_agents.product_center.product_management_agent import ProductManagementAgent, EXAMPLE_COMMANDS
from ai_agents.product_center_multi_agent_manager import ProductCenterMultiAgentManager
from typing import Optional, List, Dict, Any
import os
import json
from config.llm_config_loader import llm_config
from utils.langfuse_handler import get_global_langfuse_handler

router = APIRouter()

# グローバルインスタンス管理
single_agent_instance = None
multi_agent_manager_instance = None
agent_director_instance = None

def get_single_agent(llm_type: str = None):
    """単一エージェントインスタンスを取得または作成"""
    global single_agent_instance

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
    if single_agent_instance is None or single_agent_instance.llm_type != llm_type:
        api_key = os.getenv("OPENAI_API_KEY")

        # 新しいエージェントインスタンスを作成
        single_agent_instance = ProductManagementAgent(api_key, llm_type=llm_type)
        print(f"🔄 単一エージェントを{llm_type}で初期化しました")

    return single_agent_instance

def get_multi_agent_manager(llm_type: str = None):
    """マルチエージェントマネージャーインスタンスを取得または作成"""
    global multi_agent_manager_instance

    # デフォルトモデルを設定
    if not llm_type:
        llm_type = llm_config.get_default_model()

    # モデル利用可能性をチェック
    is_available, message = llm_config.validate_model_availability(llm_type)
    if not is_available:
        print(f"⚠️ {message}")
        # フォールバックモデルを使用
        llm_type = llm_config.get_default_model()

    # マネージャーが存在しない場合は作成
    if multi_agent_manager_instance is None:
        api_key = os.getenv("OPENAI_API_KEY")

        # 新しいマネージャーインスタンスを作成
        multi_agent_manager_instance = ProductCenterMultiAgentManager(
            api_key=api_key, 
            llm_type=llm_type
        )
        print(f"🔄 マルチエージェントマネージャーを{llm_type}で初期化しました")

    return multi_agent_manager_instance

def get_agent_director(llm_type: str = None):
    """エージェントディレクターインスタンスを取得または作成"""
    global agent_director_instance

    # デフォルトモデルを設定
    if not llm_type:
        llm_type = llm_config.get_default_model()

    # モデル利用可能性をチェック
    is_available, message = llm_config.validate_model_availability(llm_type)
    if not is_available:
        print(f"⚠️ {message}")
        # フォールバックモデルを使用
        llm_type = llm_config.get_default_model()

    # ディレクターが存在しない場合は作成
    if agent_director_instance is None:
        api_key = os.getenv("OPENAI_API_KEY")

        # 新しいディレクターインスタンスを作成
        from ai_agents.agent_director import AgentDirector
        agent_director_instance = AgentDirector(api_key=api_key, llm_type=llm_type)
        print(f"🔄 エージェントディレクターを{llm_type}で初期化しました")

    return agent_director_instance

# === Request/Response Models ===
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    llm_type: Optional[str] = "ollama"
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MultiAgentChatRequest(ChatRequest):
    agent_type: Optional[str] = None  # 指定エージェント（省略時は自動ルーティング）
    enable_collaboration: bool = True  # 協作モード有効化

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    html_content: Optional[str] = None
    action_type: Optional[str] = None
    workflow_step: Optional[str] = None
    llm_type_used: Optional[str] = None
    agent_type: Optional[str] = None
    next_actions: Optional[str] = None
    trace_id: Optional[str] = None  # 評価用のLangfuse trace ID
    conversation_id: Optional[int] = None  # base_agentから取得した会話ID

class MultiAgentChatResponse(ChatResponse):
    routing_decision: Optional[Dict[str, Any]] = None
    collaboration_mode: bool = False
    collaboration_results: Optional[List[Dict[str, Any]]] = None

class RoutingAnalysisRequest(BaseModel):
    command: str
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class RoutingAnalysisResponse(BaseModel):
    selected_agent: str
    confidence: float
    confidence_level: str
    reasoning: str
    alternative_agents: List[str]
    requires_collaboration: bool
    collaboration_sequence: List[str]

class RoutingFeedbackRequest(BaseModel):
    command: str
    predicted_agent: str
    actual_agent: str
    success: bool
    user_feedback: Optional[str] = None

class SimulationRequest(BaseModel):
    test_commands: List[str]

# === 単一エージェント API ===
@router.post("/single-agent/chat", response_model=ChatResponse)
async def single_agent_chat(request: ChatRequest):
    """単一エージェントとの対話"""
    try:
        # リクエストからllm_typeを取得
        llm_type = getattr(request, 'llm_type', 'ollama')

        # 単一エージェントを取得
        agent = get_single_agent(llm_type)

        # コマンドを処理
        response = agent.process_command(
            request.message, 
            llm_type=llm_type,
            session_id=request.session_id,
            user_id=request.user_id
        )

        # レスポンス解析と構築
        return _parse_agent_response(response, request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"単一エージェント処理に失敗しました: {str(e)}")

@router.get("/single-agent/info")
async def get_single_agent_info(llm_type: Optional[str] = Query(None)):
    """単一エージェントの情報を取得"""
    try:
        agent = get_single_agent(llm_type)
        return agent.get_agent_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エージェント情報取得に失敗しました: {str(e)}")

# === マルチエージェント API ===
@router.post("/multi-agent/chat", response_model=MultiAgentChatResponse)
async def multi_agent_chat(request: MultiAgentChatRequest):
    """インテリジェントマルチエージェントとの対話"""
    try:
        # マルチエージェントマネージャーを取得
        manager = get_multi_agent_manager(request.llm_type)

        # 協作モードの判定
        if request.enable_collaboration:
            response = manager.process_collaborative_command(
                command=request.message,
                context=request.context,
                llm_type=request.llm_type,
                session_id=request.session_id,
                user_id=request.user_id
            )
        else:
            response = manager.process_command(
                command=request.message,
                agent_type=request.agent_type,
                context=request.context,
                llm_type=request.llm_type,
                session_id=request.session_id,
                user_id=request.user_id
            )

        # マルチエージェントレスポンス解析
        return _parse_multi_agent_response(response, request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"マルチエージェント処理に失敗しました: {str(e)}")

@router.post("/director-agent/chat", response_model=ChatResponse)
async def agent_director_chat(request: ChatRequest):
    """エージェントディレクターを使用したマルチエージェントとの対話"""
    try:
        # エージェントディレクターを取得
        director = get_agent_director(request.llm_type)

        # コマンドを処理
        response = director.process_command(
            request.message,
            llm_type=request.llm_type,
            session_id=request.session_id,
            user_id=request.user_id,
            is_entry_agent=True,
        )

        # レスポンス解析と構築
        return _parse_agent_response(response, request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エージェントディレクター処理に失敗しました: {str(e)}")

@router.post("/multi-agent/routing/analyze", response_model=RoutingAnalysisResponse)
async def analyze_routing(request: RoutingAnalysisRequest):
    """コマンドのルーティング分析（実際の処理は行わない）"""
    try:
        manager = get_multi_agent_manager()
        routing_decision = manager.analyze_command_routing(request.command, request.context)

        return RoutingAnalysisResponse(
            selected_agent=routing_decision.selected_agent,
            confidence=routing_decision.confidence,
            confidence_level=routing_decision.confidence_level.value,
            reasoning=routing_decision.reasoning,
            alternative_agents=routing_decision.alternative_agents,
            requires_collaboration=routing_decision.requires_collaboration,
            collaboration_sequence=routing_decision.collaboration_sequence
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ルーティング分析に失敗しました: {str(e)}")

@router.post("/multi-agent/routing/feedback")
async def provide_routing_feedback(request: RoutingFeedbackRequest):
    """ルーティング結果のフィードバックを提供"""
    try:
        manager = get_multi_agent_manager()
        manager.provide_routing_feedback(
            request.command,
            request.predicted_agent,
            request.actual_agent,
            request.success,
            request.user_feedback
        )
        return {"message": "フィードバックが記録されました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"フィードバック記録に失敗しました: {str(e)}")

@router.post("/multi-agent/routing/simulate")
async def simulate_routing(request: SimulationRequest):
    """ルーティングをシミュレーション"""
    try:
        manager = get_multi_agent_manager()
        simulation_result = manager.simulate_routing(request.test_commands)
        return simulation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ルーティングシミュレーションに失敗しました: {str(e)}")

# === システム情報 API ===
@router.get("/multi-agent/agents")
async def get_available_agents():
    """利用可能なエージェント一覧を取得"""
    try:
        manager = get_multi_agent_manager()
        return {
            "available_agents": manager.get_available_agents(),
            "agent_info": manager.get_agent_info()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エージェント一覧取得に失敗しました: {str(e)}")

@router.get("/multi-agent/capabilities")
async def get_agent_capabilities():
    """全エージェントの能力情報を取得"""
    try:
        manager = get_multi_agent_manager()
        return manager.get_agent_capabilities()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"エージェント能力情報取得に失敗しました: {str(e)}")

@router.get("/multi-agent/analytics")
async def get_routing_analytics():
    """ルーティング分析情報を取得"""
    try:
        manager = get_multi_agent_manager()
        return manager.get_routing_analytics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ルーティング分析情報取得に失敗しました: {str(e)}")

@router.get("/multi-agent/status")
async def get_system_status():
    """システム全体の状態を取得"""
    try:
        manager = get_multi_agent_manager()
        return manager.get_system_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"システム状態取得に失敗しました: {str(e)}")

# === 共通 API ===
@router.get("/examples")
async def get_example_commands():
    """サンプルコマンドを取得"""
    return {
        "single_agent_examples": EXAMPLE_COMMANDS,
        "multi_agent_examples": [
            "商品在庫を確認したい",
            "JAN123456789の価格を1500円に変更",
            "在庫不足の商品をすべて棚下げ",
            "商品管理画面を生成してください",
            "コーヒー商品の販売状況を分析",
            "顧客からの商品問い合わせに対応",
            "新商品のマーケティング戦略を検討"
        ],
        "description": "エージェントと対話できるサンプルコマンドです"
    }

@router.delete("/reset")
async def reset_agents():
    """全エージェントをリセット"""
    try:
        global single_agent_instance, multi_agent_manager_instance
        single_agent_instance = None
        multi_agent_manager_instance = None
        return {"message": "全エージェントがリセットされました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"リセットに失敗しました: {str(e)}")

# === LLM管理 API ===
@router.post("/llm/switch/{agent_type}")
async def switch_agent_llm(agent_type: str, new_llm_type: str):
    """指定エージェントのLLMを切り替え"""
    try:
        if agent_type == "single":
            # agent = get_single_agent()
            agent = get_agent_director()
            agent.switch_llm(new_llm_type)
            return {"message": f"単一エージェントのLLMを{new_llm_type}に切り替えました"}
        elif agent_type in ["multi", "routing"]:
            manager = get_multi_agent_manager()
            if agent_type == "routing":
                success = manager.switch_routing_llm(new_llm_type)
            else:
                # 特定のエージェントのLLMを切り替え（将来の拡張用）
                success = True

            if success:
                return {"message": f"マルチエージェントの{agent_type}LLMを{new_llm_type}に切り替えました"}
            else:
                raise HTTPException(status_code=500, detail="LLM切り替えに失敗しました")
        else:
            raise HTTPException(status_code=400, detail="無効なエージェントタイプです")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM切り替えに失敗しました: {str(e)}")

@router.get("/llm/available")
async def get_available_llms():
    """利用可能なLLM一覧を取得"""
    try:
        agent = get_single_agent()
        return {"available_llms": agent.get_available_llms()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM一覧取得に失敗しました: {str(e)}")

# === ヘルパー関数 ===
def _parse_agent_response(response: str, request: ChatRequest) -> ChatResponse:
    """エージェントレスポンスを解析してChatResponseに変換"""
    html_content = None
    action_type = None
    workflow_step = None
    llm_type_used = request.llm_type
    agent_type = None
    next_actions = None
    trace_id = None
    conversation_id = None

    # Langfuseハンドラーを取得
    langfuse_handler = get_global_langfuse_handler()

    try:
        if response.strip().startswith('{'):
            response_data = json.loads(response)
            html_content = response_data.get("html_content")
            action_type = response_data.get("action_type")
            workflow_step = response_data.get("current_step")
            llm_type_used = response_data.get("llm_type_used", request.llm_type)
            agent_type = response_data.get("agent_type")
            next_actions = response_data.get("next_actions")
            trace_id = response_data.get("trace_id")
            conversation_id = response_data.get("conversation_id")  # base_agentから返されるconversation_idを取得

            # ユーザー向けメッセージを取得
            response = response_data.get("message", response)
    except (json.JSONDecodeError, KeyError):
        pass

    # trace_idが設定されていない場合、現在のtraceから取得を試行
    if not trace_id and langfuse_handler.is_available():
        try:
            # CallbackHandlerから現在のtrace_idを取得
            trace_id = langfuse_handler.get_current_trace_id()
            if trace_id:
                print(f"✅ 現在のtrace_idを取得しました: {trace_id}")
        except Exception as e:
            print(f"⚠️ trace_id取得エラー: {e}")

    return ChatResponse(
        response=response,
        session_id=request.session_id,
        user_id=request.user_id,
        html_content=html_content,
        action_type=action_type,
        workflow_step=workflow_step,
        llm_type_used=llm_type_used,
        agent_type=agent_type,
        next_actions=next_actions,
        trace_id=trace_id,
        conversation_id=conversation_id  # base_agentから取得したconversation_idを設定
    )

def _parse_multi_agent_response(response: str, request: MultiAgentChatRequest) -> MultiAgentChatResponse:
    """マルチエージェントレスポンスを解析してMultiAgentChatResponseに変換"""
    # 基本レスポンスを解析
    base_response = _parse_agent_response(response, request)

    routing_decision = None
    collaboration_mode = False
    collaboration_results = None

    try:
        if response.strip().startswith('{'):
            response_data = json.loads(response)
            routing_decision = response_data.get("routing_decision")
            collaboration_mode = response_data.get("collaboration_mode", False)
            collaboration_results = response_data.get("collaboration_results")
    except (json.JSONDecodeError, KeyError):
        pass

    return MultiAgentChatResponse(
        response=base_response.response,
        session_id=base_response.session_id,
        user_id=base_response.user_id,
        html_content=base_response.html_content,
        action_type=base_response.action_type,
        workflow_step=base_response.workflow_step,
        llm_type_used=base_response.llm_type_used,
        agent_type=base_response.agent_type,
        next_actions=base_response.next_actions,
        trace_id=base_response.trace_id,
        routing_decision=routing_decision,
        collaboration_mode=collaboration_mode,
        collaboration_results=collaboration_results
    )

# === 従来のAPI（後方互換性） ===
@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent_endpoint(request: ChatRequest):
    """従来のchatエンドポイント（単一エージェント用、後方互換性）"""
    return await single_agent_chat(request)

@router.post("/execute-product-management-workflow")
async def execute_product_management_workflow(request: ChatRequest):
    """従来の商品管理ワークフロー実行（後方互換性）"""
    try:
        agent = get_single_agent(request.llm_type)
        response = agent.process_command(
            request.message, 
            session_id=request.session_id,
            llm_type=request.llm_type
        )

        # レスポンス解析と構築（trace_idを含む）
        return _parse_agent_response(response, request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ワークフロー実行に失敗しました: {str(e)}")
