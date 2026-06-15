from agents.base_agent import BaseAgent, OUTPUT_FORMAT_INSTRUCTION
from agents.models import AgentOutput

FRAUD_PROMPT = """Tu es un analyste fraude spécialisé dans la détection d'anomalies comportementales sur les transactions bancaires.

Signaux à analyser :
- Montant anormalement élevé par rapport à l'historique du client (ratio > 2x = suspect, > 3x = très suspect)
- Transaction en dehors des heures ouvrables (avant 8h ou après 20h UTC)
- Nouvelle contrepartie jamais utilisée auparavant
- Compte récemment ouvert (< 6 mois) effectuant de grosses transactions
- Pays de destination à risque élevé

Transaction à analyser :
{transaction_context}

{format_instruction}

Règles de vote :
- ESCALATE_SAR si plusieurs signaux cumulés (2+ signaux forts)
- ESCALATE_HUMAN si 1 signal fort isolé mais inexpliqué
- CLEAR si comportement cohérent avec le profil client
"""


class FraudAgent(BaseAgent):
    def __init__(self):
        super().__init__("fraud-agent")

    def analyze(self, transaction: dict, round_num: int = 1) -> AgentOutput:
        prompt = FRAUD_PROMPT.format(
            transaction_context=self._format_context(transaction),
            format_instruction=OUTPUT_FORMAT_INSTRUCTION
        )
        return self._build_output(self._call_llm(prompt), round_num)

    def _format_context(self, t: dict) -> str:
        ratio = t.get("amount_vs_average_ratio")
        ratio_str = f"{ratio}x la moyenne" if ratio else "première grosse transaction (pas de moyenne)"
        return (
            f"- Montant : {t['amount']} {t['currency']} ({ratio_str})\n"
            f"- Heure : {t['time_utc']} UTC ({t['day_of_week']}) — hors heures ouvrables : {t.get('is_outside_business_hours')}\n"
            f"- Nouvelle contrepartie : {t.get('is_new_counterparty')}\n"
            f"- Profil expéditeur : {t['from_profile']}\n"
            f"- Profil destinataire : {t['to_profile']} ({t.get('to_country', '')})\n"
            f"- Transactions ce mois : {t.get('from_transaction_count_this_month', 'N/A')}"
        )
