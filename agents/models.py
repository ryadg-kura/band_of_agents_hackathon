from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone


class RiskLevel(str, Enum):
    HIGH = "HIGH"
    WARN = "WARN"
    CLEAR = "CLEAR"


class Vote(str, Enum):
    ESCALATE_SAR = "ESCALATE_SAR"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"
    CLEAR = "CLEAR"


@dataclass
class AgentOutput:
    agent: str
    round: int
    risk_level: RiskLevel
    confidence: float
    reasoning: str
    vote: Vote
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "round": self.round,
            "type": "analysis",
            "risk_level": self.risk_level.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "vote": self.vote.value,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentOutput":
        return cls(
            agent=data["agent"],
            round=data["round"],
            risk_level=RiskLevel(data["risk_level"]),
            confidence=data["confidence"],
            reasoning=data["reasoning"],
            vote=Vote(data["vote"]),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )
