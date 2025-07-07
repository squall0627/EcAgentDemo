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
    HIGH = "high"  # 90%以上の信頼度
    MEDIUM = "medium"  # 70-89%の信頼度
    LOW = "low"  # 50-69%の信頼度
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

    def format_for_llm_tool_description(self) -> str:
        """
        Format agent capability as an LLM-friendly tool description.
        
        Returns:
            str: Formatted description string optimized for LLM tool consumption
        """
        try:
            # Create LLM-friendly structured JSON format
            llm_friendly_capability = {
                "agent_type": self.agent_type,
                "description": self.description,
                "primary_domains": self.primary_domains,
                "key_functions": self.key_functions,
                "example_commands": self.example_commands,
                "collaboration_needs": self.collaboration_needs or []
            }

            # Format JSON for human readability
            formatted_json = json.dumps(llm_friendly_capability, ensure_ascii=False, indent=2)

            return f"""
Specialized agent tool that executes the following agent capabilities:

{formatted_json}

This agent provides comprehensive functionality based on the above capability definition.
"""
        except Exception as e:
            raise e


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
