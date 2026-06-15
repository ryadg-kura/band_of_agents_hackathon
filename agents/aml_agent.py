from agents.base_agent import BaseAgent, OUTPUT_FORMAT_INSTRUCTION
from agents.models import AgentOutput

AML_PROMPT = """Tu es un analyste AML (Anti-Money Laundering) expert. Tu analyses des transactions financières pour détecter des patterns de blanchiment d'argent.

Patterns à détecter :
- STRUCTURING : montant juste sous un seuil légal (ex: $47,500 sous $50,000)
- LAYERING : transactions multiples qui semblent déplacer des fonds entre comptes
- SMURFING : fractionnement de gros montants en petites transactions
- Comportement incohérent avec le profil client (montant anormal, fréquence anormale)

Transaction à analyser :
{transaction_context}

{format_instruction}

Règles de vote :
- ESCALATE_SAR si tu détectes un pattern AML clair ou forte suspicion
- ESCALATE_HUMAN si tu es incertain mais préoccupé
- CLEAR si aucun signal AML
"""


class AMLAgent(BaseAgent):
    def __init__(self):
        super().__init__("aml-agent")

    def analyze(self, transaction: dict, round_num: int = 1) -> AgentOutput:
        prompt = AML_PROMPT.format(
            transaction_context=self._format_transaction(transaction),
            format_instruction=OUTPUT_FORMAT_INSTRUCTION
        )
        return self._build_output(self._call_llm(prompt), round_num)

    def analyze_with_context(self, transaction: dict, other_analyses: str, round_num: int = 2) -> AgentOutput:
        prompt = AML_PROMPT.format(
            transaction_context=self._format_transaction(transaction),
            format_instruction=OUTPUT_FORMAT_INSTRUCTION
        ) + f"\n\nContexte — analyses des autres agents :\n{other_analyses}\n\nRévise ou confirme ta position."
        return self._build_output(self._call_llm(prompt), round_num)

    def _format_transaction(self, t: dict) -> str:
        return (
            f"- ID : {t['id']}\n"
            f"- Montant : {t['amount']} {t['currency']}\n"
            f"- Expéditeur : {t['from_name']} ({t['from_profile']})\n"
            f"- Destinataire : {t['to']} ({t.get('to_country', '')}) — {t['to_profile']}\n"
            f"- Heure : {t['time_utc']} UTC ({t['day_of_week']})\n"
            f"- Ratio montant/moyenne : {t.get('amount_vs_average_ratio', 'N/A')}x\n"
            f"- Hors heures ouvrables : {t.get('is_outside_business_hours', 'N/A')}\n"
            f"- Nouvelle contrepartie : {t.get('is_new_counterparty', 'N/A')}\n"
            f"- Flaggé par : {t['flagged_by']}"
        )
