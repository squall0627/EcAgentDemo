from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ai_agents.product_center.product_center_agent_manager import ProductCenterAgentManager
from ai_agents.product_center.product_detail_agent import ProductDetailAgent, EXAMPLE_COMMANDS
from typing import Optional, List, Dict, Any
import os
import json
import asyncio
from config.llm_config_loader import llm_config
from config.agent_hierarchy_loader import agent_hierarchy_loader
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
        single_agent_instance = ProductDetailAgent(api_key, llm_type=llm_type)
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
    if multi_agent_manager_instance is None or multi_agent_manager_instance.llm_type != llm_type:
        api_key = os.getenv("OPENAI_API_KEY")

        # 新しいマネージャーインスタンスを作成
        multi_agent_manager_instance = ProductCenterAgentManager(
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
    agent_type: Optional[str] = None  # 指定エージェント（省略時はデフォルトエージェント）
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
    next_actions: Optional[str | list[str]] = None
    trace_id: Optional[str] = None  # 評価用のLangfuse trace ID
    conversation_id: Optional[int] = None  # base_agentから取得した会話ID
    error_message: Optional[str] = None

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
        # リクエストからllm_typeとagent_typeを取得
        llm_type = getattr(request, 'llm_type', 'ollama')
        agent_type = getattr(request, 'agent_type', None)

        print(f"🔍 単一エージェントチャットリクエスト: {request.message}, LLM: {llm_type}, エージェントタイプ: {agent_type}")
        # エージェントを動的に選択
        if agent_type and agent_type != 'AgentDirector':
            # 指定されたエージェントタイプを使用
            api_key = os.getenv("OPENAI_API_KEY")
            agent = agent_hierarchy_loader.create_agent_instance(
                agent_key=agent_type,
                api_key=api_key,
                llm_type=llm_type,
                use_langfuse=True
            )
        else:
            # デフォルトエージェントを使用
            agent = get_single_agent(llm_type)

        print(f"🔄 単一エージェントを{agent.agent_name}で初期化しました")

        try:
            # 非同期メソッドを使用して処理（内部でThreadPoolExecutorとタイムアウト処理を実行）
            response = await agent.process_command_async(
                command=request.message, 
                llm_type=llm_type,
                session_id=request.session_id,
                user_id=request.user_id,
                is_entry_agent=True,
                timeout=120.0
            )
        except asyncio.TimeoutError:
            print(f"⏰ エージェント処理がタイムアウトしました (120秒)")
            raise HTTPException(
                status_code=504, 
                detail="エージェント処理がタイムアウトしました。しばらく待ってから再試行してください。"
            )

        print(f"✅ 単一エージェント処理完了: {response}")
        # レスポンス解析と構築
        return _parse_agent_response(response, request)

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        print(f"⚠️ 単一エージェント処理中にエラー: {str(e)}")
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
        # リクエストからllm_typeを取得
        llm_type = getattr(request, 'llm_type', 'ollama')

        # 単一エージェントを取得
        agent = get_multi_agent_manager(llm_type)

        try:
            # 非同期メソッドを使用して処理（内部でThreadPoolExecutorとタイムアウト処理を実行）
            response = await agent.process_command_async(
                command=request.message,
                llm_type=llm_type,
                session_id=request.session_id,
                user_id=request.user_id,
                is_entry_agent=True,
                timeout=120.0
            )
        except asyncio.TimeoutError:
            print(f"⏰ マルチエージェント処理がタイムアウトしました (120秒)")
            raise HTTPException(
                status_code=504, 
                detail="マルチエージェント処理がタイムアウトしました。しばらく待ってから再試行してください。"
            )

        # レスポンス解析と構築
        return _parse_agent_response(response, request)

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"マルチエージェント処理に失敗しました: {str(e)}")

@router.post("/director-agent/chat", response_model=ChatResponse)
async def agent_director_chat(request: ChatRequest):
    """エージェントディレクターを使用したマルチエージェントとの対話"""
    try:
        # エージェントディレクターを取得
        director = get_agent_director(request.llm_type)

        try:
            # 非同期メソッドを使用して処理（内部でThreadPoolExecutorとタイムアウト処理を実行）
            response = await director.process_command_async(
                command=request.message,
                llm_type=request.llm_type,
                session_id=request.session_id,
                user_id=request.user_id,
                is_entry_agent=True,
                timeout=120.0
            )
        except asyncio.TimeoutError:
            print(f"⏰ エージェントディレクター処理がタイムアウトしました (120秒)")
            raise HTTPException(
                status_code=504, 
                detail="エージェントディレクター処理がタイムアウトしました。しばらく待ってから再試行してください。"
            )

        # レスポンス解析と構築
        return _parse_agent_response(response, request)

    except HTTPException:
        # HTTPExceptionはそのまま再発生
        raise
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
def _parse_agent_response(response, request: ChatRequest) -> ChatResponse:
    """エージェントレスポンス（BaseAgentStateまたはJSON文字列）を解析してChatResponseに変換"""
    html_content = None
    action_type = None
    workflow_step = None
    llm_type_used = request.llm_type
    agent_type = None
    next_actions = None
    trace_id = None
    conversation_id = None
    error_message = None
    response_message = None

    # Langfuseハンドラーを取得
    langfuse_handler = get_global_langfuse_handler()

    try:
        # BaseAgentStateオブジェクトの場合
        if isinstance(response, dict) and "messages" in response:
            # BaseAgentStateから直接値を取得
            html_content = response.get("html_content")
            action_type = response.get("action_type")
            workflow_step = response.get("current_step")
            llm_type_used = response.get("llm_type_used", request.llm_type)
            agent_type = response.get("agent_type") or response.get("agent_name")
            next_actions = response.get("next_actions")
            if isinstance(next_actions, (dict, list)):
                try:
                    next_actions = json.dumps(next_actions, ensure_ascii=False)
                except Exception as e:
                    print(f"⚠️ next_actions JSON変換エラー: {e}")
                    next_actions = str(next_actions)

            trace_id = response.get("trace_id")
            conversation_id = response.get("conversation_id")
            error_message = response.get("error_message")
            response_message = response.get("response_message")

            # レスポンスメッセージが設定されていない場合、messagesから取得
            if not response_message and response.get("messages"):
                response_message = response["messages"][-1].content if response["messages"] else "処理が完了しました"

            # 後方互換性のため、response_dataからも取得を試行
            if not response_message and response.get("response_data"):
                response_message = response["response_data"].get("message", "処理が完了しました")

        # JSON文字列の場合（後方互換性）
        elif isinstance(response, str) and response.strip().startswith('{'):
            response_data = json.loads(response)
            html_content = response_data.get("html_content")
            action_type = response_data.get("action_type")
            workflow_step = response_data.get("current_step")
            llm_type_used = response_data.get("llm_type_used", request.llm_type)
            agent_type = response_data.get("agent_type")
            next_actions = response_data.get("next_actions")
            if isinstance(next_actions, (dict, list)):
                try:
                    next_actions = json.dumps(next_actions, ensure_ascii=False)
                except Exception as e:
                    print(f"⚠️ next_actions JSON変換エラー: {e}")
                    next_actions = str(next_actions)
            trace_id = response_data.get("trace_id")
            conversation_id = response_data.get("conversation_id")
            error_message = response_data.get("error_message")
            response_message = response_data.get("message", response)
        else:
            # 文字列レスポンスの場合
            response_message = str(response)

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"⚠️ レスポンス解析エラー: {e}")
        response_message = str(response) if response else "処理が完了しました"
    except Exception as e:
        print(f"⚠️ レスポンス処理中に予期しないエラー: {e}")
        response_message = "処理中にエラーが発生しました"

    # trace_idが設定されていない場合、現在のtraceから取得を試行
    if not trace_id and langfuse_handler.is_available():
        try:
            # CallbackHandlerから現在のtrace_idを取得
            trace_id = langfuse_handler.get_current_trace_id()
            if trace_id:
                print(f"✅ 現在のtrace_idを取得しました: {trace_id}")
        except Exception as e:
            print(f"⚠️ trace_id取得エラー: {e}")

    print(f"🔄 レスポンス解析完了: {response_message}, trace_id: {trace_id}")
    return ChatResponse(
        response=response_message or "処理が完了しました",
        session_id=request.session_id,
        user_id=request.user_id,
        html_content=html_content,
        action_type=action_type,
        workflow_step=workflow_step,
        llm_type_used=llm_type_used,
        agent_type=agent_type,
        next_actions=next_actions,
        trace_id=trace_id,
        conversation_id=conversation_id,
        error_message=error_message
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
            llm_type=request.llm_type,
            is_entry_agent=True
        )

        # レスポンス解析と構築（trace_idを含む）
        return _parse_agent_response(response, request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ワークフロー実行に失敗しました: {str(e)}")
