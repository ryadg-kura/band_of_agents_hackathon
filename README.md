# Quorum — Financial Compliance Panel

Multi-agent financial transaction compliance review system built for the [Band of Agents Hackathon](https://lablab.ai/ai-hackathons/band-of-agents-hackathon).

4 AI agents collaborate via Band to triage suspicious transactions, debate conflicting opinions, and recommend compliance actions — with a human compliance officer making the final call.

## Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd band_of_agents_hackathon

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env and add your API keys:
#   GOOGLE_API_KEY=...
#   BAND_API_KEY=...
```

## Run

```bash
# Activate venv if not already active
source .venv/bin/activate

# Run a compliance case
python main.py TXN-001   # false positive → auto-cleared
python main.py TXN-002   # conflict between agents → debate → SAR
python main.py TXN-003   # sanctions hit → immediate escalation

# Launch HITL dashboard
streamlit run dashboard/app.py
```

## Architecture

```
[Transaction] → [Enricher] → Band room "case-{id}"
                                    ↓ (parallel)
                    [AML Agent] [Sanctions Agent] [Fraud Agent]
                                    ↓
                            [Synthesis Agent]
                          detects conflicts → debate round
                                    ↓
                            [HITL Dashboard]
                         compliance officer decides
                                    ↓
                         decision logged in Band = audit trail
```

## Agents

| Agent | Role |
|---|---|
| AML Agent | Detects money laundering patterns (structuring, layering, smurfing) |
| Sanctions Agent | Screens OFAC/EU/UN/PEP lists with fuzzy matching |
| Fraud Agent | Detects behavioral anomalies (amount, time, counterparty) |
| Synthesis Agent | Arbitrates conflicts, conducts debate, produces final verdict |

## Tests

```bash
pytest tests/ -v
```
