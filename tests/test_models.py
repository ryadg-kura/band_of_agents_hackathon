from agents.models import AgentOutput, RiskLevel, Vote


def test_agent_output_serialization():
    output = AgentOutput(
        agent="aml-agent", round=1, risk_level=RiskLevel.HIGH,
        confidence=0.87, reasoning="Pattern structuring détecté", vote=Vote.ESCALATE_SAR,
    )
    data = output.to_dict()
    assert data["agent"] == "aml-agent"
    assert data["risk_level"] == "HIGH"
    assert data["vote"] == "ESCALATE_SAR"
    assert "timestamp" in data


def test_agent_output_from_dict():
    data = {
        "agent": "fraud-agent", "round": 1, "risk_level": "WARN",
        "confidence": 0.6, "reasoning": "Montant inhabituel",
        "vote": "CLEAR", "timestamp": "2026-06-15T14:32:01Z"
    }
    output = AgentOutput.from_dict(data)
    assert output.risk_level == RiskLevel.WARN
    assert output.vote == Vote.CLEAR
