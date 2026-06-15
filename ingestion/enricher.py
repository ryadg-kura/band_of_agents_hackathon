import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data"


def load_transactions() -> list[dict]:
    with open(DATA_PATH / "mock_transactions.json") as f:
        return json.load(f)


def get_transaction(txn_id: str) -> dict:
    for t in load_transactions():
        if t["id"] == txn_id:
            return t
    raise ValueError(f"Transaction {txn_id} not found")


def enrich_transaction(transaction: dict) -> dict:
    enriched = dict(transaction)

    avg = transaction.get("from_avg_transaction", 0)
    amount = transaction["amount"]

    enriched["amount_vs_average_ratio"] = round(amount / avg, 2) if avg > 0 else None
    enriched["is_high_amount"] = amount > 10000

    hour = int(transaction.get("time_utc", "12:00").split(":")[0])
    enriched["is_outside_business_hours"] = hour < 8 or hour >= 20

    enriched["is_new_counterparty"] = "1ère transaction" in transaction.get("to_profile", "")
    enriched["is_new_account"] = (
        "semaines" in transaction.get("from_profile", "") or
        "mois" in transaction.get("from_profile", "")
    )

    return enriched
