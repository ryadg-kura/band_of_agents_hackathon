from agents.base_agent import BaseAgent, OUTPUT_FORMAT_INSTRUCTION
from agents.models import AgentOutput, RiskLevel, Vote

SYNTHESIS_PROMPT = """Tu es le Synthesis Agent d'un panel de conformité financière. Tu lis les analyses de 3 agents spécialisés et tu produis un verdict final.

Analyses des agents :
{analyses_text}

Transaction :
{transaction_context}

{format_instruction}

Règles de verdict :
- Si consensus clair (3x CLEAR) → CLEAR
- Si majorité forte (2+ HIGH sans conflit logique) → ESCALATE_SAR
- Si ESCALATE_HUMAN d'un agent → ESCALATE_HUMAN
- Justifie ton raisonnement en 2-3 phrases en nommant les agents.
"""

DEBATE_PROMPT = """Tu es le Synthesis Agent. Tu as identifié un conflit entre les analyses des agents.

Analyses initiales :
{analyses_text}

Pose UNE question ciblée à l'agent dont l'opinion diverge.

Réponds avec un objet JSON :
{{
  "target_agent": "aml-agent" | "sanctions-agent" | "fraud-agent",
  "question": "ta question précise"
}}
"""


class SynthesisAgent(BaseAgent):
    def __init__(self):
        super().__init__("synthesis-agent")

    def _detect_conflict(self, analyses: list[AgentOutput]) -> bool:
        high_count = sum(1 for a in analyses if a.risk_level in (RiskLevel.HIGH, RiskLevel.WARN))
        clear_count = sum(1 for a in analyses if a.risk_level == RiskLevel.CLEAR)
        strong_majority = high_count >= 2 and clear_count == 1 and all(
            a.risk_level != RiskLevel.WARN for a in analyses if a.risk_level != RiskLevel.CLEAR
        )
        return high_count >= 1 and clear_count >= 1 and not strong_majority

    def _requires_immediate_escalation(self, analyses: list[AgentOutput]) -> bool:
        return any(a.vote == Vote.ESCALATE_HUMAN for a in analyses)

    def _format_analyses(self, analyses: list[AgentOutput]) -> str:
        return "\n\n".join(
            f"[{a.agent}] Risk: {a.risk_level.value} | Vote: {a.vote.value}\nRaisonnement: {a.reasoning}"
            for a in analyses
        )

    def synthesize(self, analyses: list[AgentOutput], transaction: dict) -> dict:
        if self._requires_immediate_escalation(analyses):
            return {
                "verdict": AgentOutput(
                    agent=self.agent_name, round=2,
                    risk_level=RiskLevel.HIGH, confidence=0.99,
                    reasoning="ESCALATE_HUMAN demandé par au moins un agent. Escalade immédiate sans débat.",
                    vote=Vote.ESCALATE_HUMAN,
                ),
                "debate": False,
            }

        analyses_text = self._format_analyses(analyses)
        txn_ctx = f"Montant: {transaction['amount']} {transaction['currency']} | Destinataire: {transaction['to']}"

        if self._detect_conflict(analyses):
            raw = self._call_llm(DEBATE_PROMPT.format(analyses_text=analyses_text))
            return {"debate": True, "target_agent": raw["target_agent"], "question": raw["question"]}

        prompt = SYNTHESIS_PROMPT.format(
            analyses_text=analyses_text,
            transaction_context=txn_ctx,
            format_instruction=OUTPUT_FORMAT_INSTRUCTION
        )
        return {"verdict": self._build_output(self._call_llm(prompt), 2), "debate": False}

    def final_verdict(self, analyses: list[AgentOutput], debate_response: AgentOutput, transaction: dict) -> AgentOutput:
        all_analyses = analyses + [debate_response]
        txn_ctx = f"Montant: {transaction['amount']} {transaction['currency']} | Destinataire: {transaction['to']}"
        prompt = SYNTHESIS_PROMPT.format(
            analyses_text=self._format_analyses(all_analyses),
            transaction_context=txn_ctx,
            format_instruction=OUTPUT_FORMAT_INSTRUCTION
        )
        return self._build_output(self._call_llm(prompt), 3)
