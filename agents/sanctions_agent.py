import json
from pathlib import Path
from agents.base_agent import BaseAgent, OUTPUT_FORMAT_INSTRUCTION
from agents.models import AgentOutput, RiskLevel, Vote

DATA_PATH = Path(__file__).parent.parent / "data"

SANCTIONS_PROMPT = """Tu es un spécialiste du screening sanctions. Tu évalues les résultats d'un screening contre les listes OFAC, EU et UN.

Transaction :
{transaction_context}

Résultat du screening automatique :
{screening_result}

{format_instruction}

Règles de vote :
- ESCALATE_HUMAN si une correspondance directe est trouvée sur une liste sanctions
- ESCALATE_SAR si correspondance partielle (fuzzy match)
- CLEAR si aucune correspondance
"""


class SanctionsAgent(BaseAgent):
    def __init__(self):
        super().__init__("sanctions-agent")
        with open(DATA_PATH / "sanctions_list.json") as f:
            self._sanctions = json.load(f)["entries"]

    def _screen_name(self, name: str, country: str) -> dict:
        name_lower = name.lower()
        for entry in self._sanctions:
            entry_lower = entry["name"].lower()
            if entry_lower == name_lower:
                return {"matched": True, "entry": entry, "score": 1.0, "list": entry["list"]}
            entry_words = set(entry_lower.split())
            name_words = set(name_lower.split())
            common = entry_words & name_words
            if entry_words and len(common) / len(entry_words) >= 0.7:
                return {"matched": True, "entry": entry, "score": len(common) / len(entry_words), "list": entry["list"]}
        return {"matched": False}

    def analyze(self, transaction: dict, round_num: int = 1) -> AgentOutput:
        screening = self._screen_name(transaction["to"], transaction.get("to_country", ""))

        if screening["matched"] and transaction["amount"] > 500000:
            return AgentOutput(
                agent=self.agent_name,
                round=round_num,
                risk_level=RiskLevel.HIGH,
                confidence=screening["score"],
                reasoning=(
                    f"Correspondance sanctions : {screening['entry']['name']} "
                    f"sur liste {screening['entry']['list']}. Montant > $500K — escalade immédiate."
                ),
                vote=Vote.ESCALATE_HUMAN,
            )

        screening_text = (
            f"MATCH : {screening['entry']['name']} (liste {screening['entry']['list']}, score {screening['score']:.2f})"
            if screening["matched"]
            else "Aucune correspondance trouvée sur les listes OFAC, EU, UN, PEP."
        )
        prompt = SANCTIONS_PROMPT.format(
            transaction_context=f"Destinataire : {transaction['to']} ({transaction.get('to_country', '')})",
            screening_result=screening_text,
            format_instruction=OUTPUT_FORMAT_INSTRUCTION
        )
        return self._build_output(self._call_llm(prompt), round_num)
