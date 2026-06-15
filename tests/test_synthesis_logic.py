from agents.synthesis_agent import SynthesisAgent
from agents.models import AgentOutput, RiskLevel, Vote


def make_output(agent, risk, vote):
    return AgentOutput(
        agent=agent, round=1, risk_level=RiskLevel(risk),
        confidence=0.8, reasoning="test", vote=Vote(vote)
    )


def test_no_conflict_all_clear():
    agent = SynthesisAgent()
    analyses = [
        make_output("aml-agent", "CLEAR", "CLEAR"),
        make_output("sanctions-agent", "CLEAR", "CLEAR"),
        make_output("fraud-agent", "CLEAR", "CLEAR"),
    ]
    assert agent._detect_conflict(analyses) is False


def test_no_conflict_strong_majority():
    agent = SynthesisAgent()
    analyses = [
        make_output("aml-agent", "HIGH", "ESCALATE_SAR"),
        make_output("sanctions-agent", "CLEAR", "CLEAR"),
        make_output("fraud-agent", "HIGH", "ESCALATE_SAR"),
    ]
    assert agent._detect_conflict(analyses) is False


def test_conflict_detected():
    agent = SynthesisAgent()
    analyses = [
        make_output("aml-agent", "HIGH", "ESCALATE_SAR"),
        make_output("sanctions-agent", "CLEAR", "CLEAR"),
        make_output("fraud-agent", "WARN", "ESCALATE_HUMAN"),
    ]
    assert agent._detect_conflict(analyses) is True


def test_immediate_escalation():
    agent = SynthesisAgent()
    analyses = [
        make_output("aml-agent", "HIGH", "ESCALATE_SAR"),
        make_output("sanctions-agent", "HIGH", "ESCALATE_HUMAN"),
        make_output("fraud-agent", "HIGH", "ESCALATE_SAR"),
    ]
    assert agent._requires_immediate_escalation(analyses) is True
