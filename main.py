import asyncio
import json
import sys
from dotenv import load_dotenv

load_dotenv()

from ingestion.enricher import get_transaction, enrich_transaction
from agents.aml_agent import AMLAgent
from agents.sanctions_agent import SanctionsAgent
from agents.fraud_agent import FraudAgent
from agents.synthesis_agent import SynthesisAgent
from agents.models import AgentOutput, Vote
from band.client import BandClient


async def run_round1(transaction: dict, aml: AMLAgent, sanctions: SanctionsAgent, fraud: FraudAgent) -> list[AgentOutput]:
    loop = asyncio.get_event_loop()
    results = await asyncio.gather(
        loop.run_in_executor(None, aml.analyze, transaction),
        loop.run_in_executor(None, sanctions.analyze, transaction),
        loop.run_in_executor(None, fraud.analyze, transaction),
    )
    return list(results)


def run_case(txn_id: str, band: BandClient) -> dict:
    print(f"\n{'='*60}")
    print(f"CASE OUVERT : {txn_id}")
    print(f"{'='*60}")

    transaction = enrich_transaction(get_transaction(txn_id))
    room = band.join_room(f"case-{txn_id}")
    room.post_message({"type": "case_opened", "transaction": transaction})

    aml = AMLAgent()
    sanctions = SanctionsAgent()
    fraud = FraudAgent()
    synthesis = SynthesisAgent()

    print("\n[ROUND 1] Analyses indépendantes en cours...")
    analyses = asyncio.run(run_round1(transaction, aml, sanctions, fraud))

    for analysis in analyses:
        print(f"  {analysis.agent}: {analysis.risk_level.value} — {analysis.reasoning[:80]}...")
        room.post_message(analysis.to_dict())

    print("\n[ROUND 2] Synthesis Agent analyse les résultats...")
    synthesis_result = synthesis.synthesize(analyses, transaction)

    if synthesis_result["debate"]:
        target = synthesis_result["target_agent"]
        question = synthesis_result["question"]
        print(f"\n[DÉBAT] Synthesis challenge {target} : {question}")
        room.post_message({"type": "debate_request", "target": target, "question": question})

        other_analyses_text = "\n".join(
            f"{a.agent}: {a.risk_level.value} — {a.reasoning}"
            for a in analyses if a.agent != target
        )
        agent_map = {"aml-agent": aml, "sanctions-agent": sanctions, "fraud-agent": fraud}
        debate_response = agent_map[target].analyze_with_context(transaction, other_analyses_text, round_num=2)
        print(f"  {target} répond : {debate_response.risk_level.value} — {debate_response.reasoning[:80]}...")
        room.post_message(debate_response.to_dict())

        final = synthesis.final_verdict(analyses, debate_response, transaction)
    else:
        final = synthesis_result["verdict"]

    print(f"\n[VERDICT FINAL] {final.vote.value} — {final.reasoning}")
    room.post_message({**final.to_dict(), "type": "final_verdict"})

    if final.vote in (Vote.ESCALATE_SAR, Vote.ESCALATE_HUMAN):
        band.post_to_escalations(case_id=txn_id, verdict=final.vote.value, summary=final.reasoning)
        print("  → Escalade postée dans room 'escalations'")

    return {"case_id": txn_id, "verdict": final.to_dict()}


if __name__ == "__main__":
    txn_id = sys.argv[1] if len(sys.argv) > 1 else "TXN-001"
    band = BandClient()
    result = run_case(txn_id, band)
    print(f"\nRésultat : {json.dumps(result, indent=2)}")
