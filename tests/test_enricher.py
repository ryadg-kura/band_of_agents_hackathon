import pytest
from ingestion.enricher import load_transactions, enrich_transaction


def test_load_transactions():
    transactions = load_transactions()
    assert len(transactions) == 3
    assert transactions[0]["id"] == "TXN-001"


def test_enrich_transaction():
    raw = {
        "id": "TXN-002", "amount": 47500, "currency": "USD",
        "from_avg_transaction": 15000, "from_transaction_count_this_month": 4,
        "time_utc": "23:47", "to_profile": "1ère transaction avec ce client",
        "from_profile": "compte ouvert il y a 3 mois",
    }
    enriched = enrich_transaction(raw)
    assert enriched["amount_vs_average_ratio"] == pytest.approx(3.17, rel=0.01)
    assert enriched["is_outside_business_hours"] is True
    assert enriched["is_high_amount"] is True
    assert enriched["is_new_counterparty"] is True
