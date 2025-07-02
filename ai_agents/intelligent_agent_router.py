import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import statistics
from datetime import datetime
from typing_extensions import deprecated

from langchain.schema import HumanMessage
from pydantic import BaseModel, Field

from llm.llm_handler import LLMHandler
from utils.langfuse_handler import LangfuseHandler

class RoutingConfidence(Enum):
    """ルーティング信頼度レベル"""
    HIGH = "high"      # 90%以上の信頼度
    MEDIUM = "medium"  # 70-89%の信頼度
    LOW = "low"        # 50-69%の信頼度
    UNCERTAIN = "uncertain"  # 50%未満の信頼度

@dataclass
class AgentCapability:
    """エージェント能力定義"""
    agent_type: str
    description: str
    primary_domains: List[str]
    key_functions: List[str]
    example_commands: List[str]
    collaboration_needs: List[str] = None  # 他エージェントとの連携が必要な場合

@dataclass
class RoutingFeedback:
    """ルーティングフィードバック情報"""
    command: str
    predicted_agent: str
    actual_agent: str
    success: bool
    user_feedback: Optional[str]
    timestamp: datetime
    confidence: float

class RoutingDecision(BaseModel):
    """ルーティング決定結果"""
    selected_agent: str = Field(description="選択されたエージェントタイプ")
    confidence: float = Field(description="信頼度 (0.0-1.0)", ge=0.0, le=1.0)
    confidence_level: RoutingConfidence = Field(description="信頼度レベル")
    reasoning: str = Field(description="選択理由")
    alternative_agents: List[str] = Field(description="代替エージェント候補", default_factory=list)
    requires_collaboration: bool = Field(description="複数エージェント連携が必要か", default=False)
    collaboration_sequence: List[str] = Field(description="連携シーケンス", default_factory=list)

@deprecated(
    "IntelligentAgentRouterは非推奨です。代わりに、AgentDirectorを使用してください。",
)
class IntelligentAgentRouter:
    """
    LLMベースのインテリジェントエージェントルーター
    自然言語コマンドを分析して最適なエージェントを選択
    """
    
    def __init__(self, api_key: str, llm_type: str = None, use_langfuse: bool = True):
        """
        インテリジェントルーター初期化
        
        Args:
            api_key: APIキー
            llm_type: LLMタイプ
            use_langfuse: Langfuse使用フラグ
        """
        self.llm_handler = LLMHandler(api_key, llm_type)
        self.langfuse_handler = LangfuseHandler(use_langfuse=use_langfuse)
        
        # ルーティング専用のLLM（ツールなし、軽量化）
        self.routing_llm = self.llm_handler.get_llm()
        
        # エージェント能力定義
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        
        # ルーティング履歴（学習用）
        self.routing_history: List[Dict[str, Any]] = []
        
        # フィードバック履歴（改善用）
        self.feedback_history: List[RoutingFeedback] = []
        
        # パフォーマンス統計
        self.performance_stats: Dict[str, Any] = {
            "total_routes": 0,
            "success_rate": 0.0,
            "agent_usage_count": {},
            "confidence_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNCERTAIN": 0}
        }
    
    def register_agent_capability(self, capability: AgentCapability):
        """
        エージェント能力を登録
        
        Args:
            capability: エージェント能力定義
        """
        self.agent_capabilities[capability.agent_type] = capability
    
    def _build_routing_prompt(self, command: str, context: Dict[str, Any] = None) -> str:
        """
        ルーティング用プロンプトを構築
        
        Args:
            command: ユーザーコマンド
            context: コンテキスト情報
            
        Returns:
            str: ルーティング用プロンプト
        """
        # エージェント能力情報を構築
        agents_info = []
        for agent_type, capability in self.agent_capabilities.items():
            agent_info = f"""
## {agent_type}
**説明**: {capability.description}
**主要ドメイン**: {', '.join(capability.primary_domains)}
**主要機能**: {', '.join(capability.key_functions)}
**コマンド例**:
{chr(10).join([f"  - {example}" for example in capability.example_commands])}
"""
            if capability.collaboration_needs:
                agent_info += f"**連携要求**: {', '.join(capability.collaboration_needs)}\n"
            
            agents_info.append(agent_info)
        
        agents_description = "\n".join(agents_info)
        
        # コンテキスト情報を追加
        context_info = ""
        if context:
            context_info = f"""
# コンテキスト情報:
{json.dumps(context, ensure_ascii=False, indent=2)}
"""
        
        # フィードバック履歴からの学習情報を追加
        learning_info = self._get_learning_insights()
        
        return f"""
あなたはマルチAgent システムの知的ルーティング専門家です。
ユーザーコマンドを分析し、最適なエージェントを選択してください。

# 利用可能なエージェント:
{agents_description}

{context_info}

{learning_info}

# ルーティング基準:
1. **ドメイン適合性**: コマンドがエージェントの専門ドメインと一致するか
2. **機能カバレッジ**: エージェントの機能でコマンドを完全に処理できるか
3. **複雑性レベル**: 単一エージェントで処理可能か、複数エージェント連携が必要か
4. **効率性**: 最も効率的に処理できるエージェントはどれか
5. **過去の実績**: 同様のコマンドでの成功実績を考慮

# 出力形式:
以下のJSON形式で応答してください：
{{
  "selected_agent": "選択されたエージェント",
  "confidence": 信頼度 (0.0-1.0),
  "confidence_level": "HIGH|MEDIUM|LOW|UNCERTAIN",
  "reasoning": "選択理由",
  "alternative_agents": ["代替エージェント候補"],
  "requires_collaboration": 複数エージェント連携が必要か (true/false),
  "collaboration_sequence": ["連携エージェントシーケンス"]
}}

# 指示:
1.  コマンドを分析し、最も適切なエージェントを **selected_agent** で選択してください。
2.  **confidence** はエージェント選択の信頼度を 0.0 から 1.0 の範囲で示してください。
3.  **confidence_level** は信頼度を HIGH, MEDIUM, LOW, UNCERTAIN のいずれかで示してください。
    - HIGH: 90%以上の信頼度
    - MEDIUM: 70-89%の信頼度
    - LOW: 50-69%の信頼度
    - UNCERTAIN: 50%未満の信頼度
4.  **reasoning** には、そのエージェントを選択した理由を簡潔に記述してください。
5.  必要に応じて、 **alternative_agents** に代替エージェントの候補を列挙してください。
6.  複数エージェントの連携が必要な場合は、 **requires_collaboration** を true に設定し、 **collaboration_sequence** に連携順序でエージェントタイプを列挙してください。
7.  JSON形式以外のテキストは含めないでください。

ユーザーコマンド:
{command}
"""

    def _get_learning_insights(self) -> str:
        """
        フィードバック履歴から学習情報を取得
        
        Returns:
            str: 学習情報
        """
        if not self.feedback_history:
            return ""
        
        # 成功パターンの分析
        successful_patterns = [
            feedback for feedback in self.feedback_history 
            if feedback.success
        ]
        
        insights = []
        if successful_patterns:
            insights.append("# 成功パターンの学習:")
            for pattern in successful_patterns[-5:]:  # 最新5件
                insights.append(f"- コマンド「{pattern.command}」は{pattern.actual_agent}で成功")
        
        # 失敗パターンの分析
        failed_patterns = [
            feedback for feedback in self.feedback_history 
            if not feedback.success
        ]
        
        if failed_patterns:
            insights.append("# 失敗パターンの学習:")
            for pattern in failed_patterns[-3:]:  # 最新3件
                insights.append(f"- コマンド「{pattern.command}」は{pattern.predicted_agent}ではなく{pattern.actual_agent}が適切")
        
        return "\n".join(insights) if insights else ""

    def _determine_confidence_level(self, confidence: float) -> RoutingConfidence:
        """
        信頼度レベルを決定
        
        Args:
            confidence: 信頼度
            
        Returns:
            RoutingConfidence: 信頼度レベル
        """
        if confidence >= 0.9:
            return RoutingConfidence.HIGH
        elif confidence >= 0.7:
            return RoutingConfidence.MEDIUM
        elif confidence >= 0.5:
            return RoutingConfidence.LOW
        else:
            return RoutingConfidence.UNCERTAIN
    
    def route(self, command: str) -> RoutingDecision:
        """
        コマンドを解析して最適なエージェントを決定
        
        Args:
            command: ユーザーコマンド
            
        Returns:
            RoutingDecision: ルーティング決定結果
        """
        return self.route_command(command)
    
    def route_command(self, command: str, context: Dict[str, Any] = None) -> RoutingDecision:
        """
        コマンドを解析して最適なエージェントを決定（コンテキスト対応版）
        
        Args:
            command: ユーザーコマンド
            context: コンテキスト情報
            
        Returns:
            RoutingDecision: ルーティング決定結果
        """
        if not self.agent_capabilities:
            raise ValueError("エージェント能力が登録されていません。先にregister_agent_capabilityを実行してください。")
        
        prompt = self._build_routing_prompt(command, context)

        try:
            # Langfuse設定を取得
            langfuse_config = self.langfuse_handler.get_config(
                step_name="intelligent_routing",
                session_id=context.get("session_id") if context else None,
                user_id=context.get("user_id") if context else None
            )

            # LLMでエージェントを選択 - invoke()メソッドとLangfuse callbackを使用
            response = self.routing_llm.invoke(
                [HumanMessage(content=prompt)],
                config=langfuse_config
            )
        
            # JSONとして解析
            routing_result = json.loads(response.content)
        
            # RoutingDecisionオブジェクトに変換
            routing_decision = RoutingDecision(**routing_result)
        
            # 信頼度レベルを決定
            routing_decision.confidence_level = self._determine_confidence_level(routing_decision.confidence)
        
            # 統計を更新
            self._update_stats(routing_decision)
        
            # ルーティング履歴に追加
            self.routing_history.append({
                "command": command,
                "context": context,
                "routing_decision": routing_decision.model_dump(),
                "prompt": prompt,
                "response": response.content,
                "timestamp": datetime.now().isoformat()
            })
        
            return routing_decision
        
        except json.JSONDecodeError as e:
            print(f"JSONデコードエラー: {e}")
            print(f"LLMの応答: {response.content}")
        
            # フォールバック: デフォルトエージェントに振り分け
            default_agent = list(self.agent_capabilities.keys())[0] if self.agent_capabilities else "default"
            return RoutingDecision(
                selected_agent=default_agent,
                confidence=0.1,
                confidence_level=RoutingConfidence.UNCERTAIN,
                reasoning=f"JSONパースエラーのためデフォルトエージェントに振り分け: {str(e)}",
                alternative_agents=list(self.agent_capabilities.keys()),
                requires_collaboration=False,
                collaboration_sequence=[]
            )
        
        except Exception as e:
            print(f"ルーティング処理エラー: {e}")
        
            # フォールバック: デフォルトエージェントに振り分け
            default_agent = list(self.agent_capabilities.keys())[0] if self.agent_capabilities else "default"
            return RoutingDecision(
                selected_agent=default_agent,
                confidence=0.1,
                confidence_level=RoutingConfidence.UNCERTAIN,
                reasoning=f"エラーのためデフォルトエージェントに振り分け: {str(e)}",
                alternative_agents=list(self.agent_capabilities.keys()),
                requires_collaboration=False,
                collaboration_sequence=[]
            )
    
    def update_routing_feedback(self, command: str, predicted_agent: str, actual_agent: str, 
                              success: bool, user_feedback: str = None):
        """
        ルーティング結果のフィードバックを更新
        
        Args:
            command: 元のコマンド
            predicted_agent: 予測されたエージェント
            actual_agent: 実際に使用されたエージェント
            success: 成功したかどうか
            user_feedback: ユーザーフィードバック
        """
        # 対応するルーティング履歴を検索
        confidence = 0.5
        for history in reversed(self.routing_history):
            if history["command"] == command:
                confidence = history["routing_decision"]["confidence"]
                break
        
        feedback = RoutingFeedback(
            command=command,
            predicted_agent=predicted_agent,
            actual_agent=actual_agent,
            success=success,
            user_feedback=user_feedback,
            timestamp=datetime.now(),
            confidence=confidence
        )
        
        self.feedback_history.append(feedback)
        
        # パフォーマンス統計を更新
        self._update_performance_stats(feedback)
    
    def _update_stats(self, routing_decision: RoutingDecision):
        """
        統計情報を更新
        
        Args:
            routing_decision: ルーティング決定結果
        """
        self.performance_stats["total_routes"] += 1
        
        # エージェント使用回数を更新
        agent = routing_decision.selected_agent
        if agent not in self.performance_stats["agent_usage_count"]:
            self.performance_stats["agent_usage_count"][agent] = 0
        self.performance_stats["agent_usage_count"][agent] += 1
        
        # 信頼度分布を更新
        confidence_level = routing_decision.confidence_level.value.upper()
        if confidence_level in self.performance_stats["confidence_distribution"]:
            self.performance_stats["confidence_distribution"][confidence_level] += 1
    
    def _update_performance_stats(self, feedback: RoutingFeedback):
        """
        パフォーマンス統計を更新
        
        Args:
            feedback: フィードバック情報
        """
        if self.feedback_history:
            success_count = sum(1 for f in self.feedback_history if f.success)
            self.performance_stats["success_rate"] = success_count / len(self.feedback_history)
    
    def get_routing_analytics(self) -> Dict[str, Any]:
        """
        ルーティング分析情報を取得
        
        Returns:
            Dict[str, Any]: 分析情報
        """
        analytics = {
            "performance_stats": self.performance_stats.copy(),
            "total_feedback_count": len(self.feedback_history),
            "total_routing_count": len(self.routing_history),
            "registered_agents": list(self.agent_capabilities.keys()),
            "recent_routing_history": [
                {
                    "command": history["command"],
                    "selected_agent": history["routing_decision"]["selected_agent"],
                    "confidence": history["routing_decision"]["confidence"],
                    "timestamp": history.get("timestamp", "不明")
                }
                for history in self.routing_history[-10:]  # 最新10件
            ]
        }
        
        # 信頼度統計を追加
        if self.routing_history:
            confidences = [
                history["routing_decision"]["confidence"] 
                for history in self.routing_history
            ]
            analytics["confidence_stats"] = {
                "average": statistics.mean(confidences),
                "median": statistics.median(confidences),
                "min": min(confidences),
                "max": max(confidences)
            }
        
        # エージェント別成功率を追加
        if self.feedback_history:
            agent_performance = {}
            for feedback in self.feedback_history:
                agent = feedback.predicted_agent
                if agent not in agent_performance:
                    agent_performance[agent] = {"total": 0, "success": 0}
                agent_performance[agent]["total"] += 1
                if feedback.success:
                    agent_performance[agent]["success"] += 1
            
            for agent, stats in agent_performance.items():
                agent_performance[agent]["success_rate"] = stats["success"] / stats["total"]
            
            analytics["agent_performance"] = agent_performance
        
        return analytics
    
    def switch_llm(self, new_llm_type: str):
        """
        LLMを切り替え
        
        Args:
            new_llm_type: 新しいLLMタイプ
        """
        self.llm_handler.switch_llm(new_llm_type)
        self.routing_llm = self.llm_handler.get_llm()
    
    def get_available_llms(self) -> List[str]:
        """
        利用可能なLLMリストを取得
        
        Returns:
            List[str]: LLMタイプリスト
        """
        return self.llm_handler.get_available_llms()
    
    def get_current_llm_type(self) -> str:
        """
        現在のLLMタイプを取得
        
        Returns:
            str: LLMタイプ
        """
        return self.llm_handler.get_current_llm_type()
    
    def clear_history(self):
        """履歴をクリア"""
        self.routing_history.clear()
        self.feedback_history.clear()
        self.performance_stats = {
            "total_routes": 0,
            "success_rate": 0.0,
            "agent_usage_count": {},
            "confidence_distribution": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "UNCERTAIN": 0}
        }
    
    def export_history(self) -> Dict[str, Any]:
        """
        履歴をエクスポート
        
        Returns:
            Dict[str, Any]: 履歴データ
        """
        return {
            "routing_history": self.routing_history,
            "feedback_history": [
                {
                    "command": f.command,
                    "predicted_agent": f.predicted_agent,
                    "actual_agent": f.actual_agent,
                    "success": f.success,
                    "user_feedback": f.user_feedback,
                    "timestamp": f.timestamp.isoformat(),
                    "confidence": f.confidence
                }
                for f in self.feedback_history
            ],
            "performance_stats": self.performance_stats,
            "agent_capabilities": {
                agent_type: {
                    "agent_type": cap.agent_type,
                    "description": cap.description,
                    "primary_domains": cap.primary_domains,
                    "key_functions": cap.key_functions,
                    "example_commands": cap.example_commands,
                    "collaboration_needs": cap.collaboration_needs
                }
                for agent_type, cap in self.agent_capabilities.items()
            }
        }