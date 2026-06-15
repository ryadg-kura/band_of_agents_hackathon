from agents.sanctions_agent import SanctionsAgent


def test_exact_match():
    agent = SanctionsAgent()
    result = agent._screen_name("Pantera Shell Corp", "Panama")
    assert result["matched"] is True
    assert result["list"] == "OFAC"


def test_no_match():
    agent = SanctionsAgent()
    result = agent._screen_name("Fournisseur Dupont SARL", "France")
    assert result["matched"] is False


def test_fuzzy_match():
    agent = SanctionsAgent()
    result = agent._screen_name("Pantera Shell Corporation", "Panama")
    assert result["matched"] is True
