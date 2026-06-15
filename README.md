# Quorum — Financial Compliance Panel

Multi-agent financial transaction triage system built for the [Band of Agents Hackathon](https://lablab.ai/ai-hackathacks/band-of-agents-hackathon) — Track 3 (Regulated & High-Stakes Workflows).

4 AI agents debate inside Band rooms, reach a verdict, then surface it to a human compliance officer via a Streamlit dashboard. Every message lands in Band = native audit trail.

---

## Stack

| Layer | Tech |
|---|---|
| LLM | Groq `llama-3.3-70b-versatile` |
| Agent coordination | [Band SDK](https://band.ai) — REST API via `httpx` |
| Dashboard | Streamlit (HITL) |
| Language | Python 3.11+ |

---

## Setup (5 min)

### 1. Prérequis

```bash
git clone <repo>
cd band_of_agents_hackathon
pip install -r requirements.txt
```

### 2. Fichier `.env` (à créer à la racine, **ne pas committer**)

```
GROQ_API_KEY=gsk_...
THENVOI_REST_URL=https://app.band.ai
THENVOI_WS_URL=wss://app.band.ai/api/v1/socket/websocket
```

### 3. Fichier `agent_config.yaml` (à créer à la racine, **ne pas committer**)

Va sur [app.band.ai](https://app.band.ai), crée 4 agents, copie leurs UUID + API keys :

```yaml
aml-agent:
  agent_id: "<uuid>"
  api_key: "<key>"

sanctions-agent:
  agent_id: "<uuid>"
  api_key: "<key>"

fraud-agent:
  agent_id: "<uuid>"
  api_key: "<key>"

synthesis-agent:
  agent_id: "<uuid>"
  api_key: "<key>"
```

### 4. Vérifie la connexion

```bash
python3 verify_setup.py
```

Doit afficher `✓` pour chaque agent + message test posté dans Band.

---

## Lancer une analyse

```bash
python3 main.py TXN-001   # Faux positif → 3x CLEAR → AUTO-CLOSE
python3 main.py TXN-002   # Conflit AML+Fraud vs Sanctions → ESCALATE_SAR → HITL
python3 main.py TXN-003   # Sanctions HIGH + $890K → ESCALATE_HUMAN immédiat
```

## Lancer le dashboard HITL

```bash
streamlit run dashboard/app.py
```

Ouvre `http://localhost:8501` — tu vois les cases escaladés, tu peux CONFIRM / OVERRIDE / ASK_MORE.

---

## Architecture

```
[Transaction] → [Enricher] → Band room "case-{txn_id}"
                                     │
                     ┌───────────────┼───────────────┐
                     ▼               ▼               ▼
               [AML Agent]  [Sanctions Agent]  [Fraud Agent]
                     │               │               │
                     └───────────────┼───────────────┘
                                     ▼
                             [Synthesis Agent]
                            détecte le conflit ?
                          ┌────────────┴────────────┐
                         Non                       Oui
                          │                         │
                    verdict direct            pose une question
                          │                  agent révise / confirme
                          │                         │
                          └────────────┬────────────┘
                                       ▼
                              CLEAR → auto-close
                         ESCALATE_SAR / _HUMAN
                                       │
                              Band room "escalations"
                                       │
                            [Dashboard Streamlit]
                        CONFIRM SAR | OVERRIDE | ASK_MORE
                                       │
                              décision dans Band
                              = audit trail complet
```

## Agents

| Agent | Rôle |
|---|---|
| AML Agent | Détecte structuring, layering, smurfing |
| Sanctions Agent | Screen OFAC / EU / UN / PEP |
| Fraud Agent | Anomalies comportementales (montant, heure, contrepartie) |
| Synthesis Agent | Arbitre les conflits, mène le débat, verdict final |

## Format message Band

Tous les agents postent au format JSON identique via `/agent/chats/{id}/events` :

```json
{
  "agent": "aml-agent",
  "round": 1,
  "type": "analysis",
  "risk_level": "HIGH",
  "confidence": 0.92,
  "reasoning": "Pattern de structuring détecté...",
  "vote": "ESCALATE_SAR",
  "timestamp": "2026-06-15T14:38:29Z"
}
```

## Tests

```bash
pytest tests/ -v
```

## Fichiers importants

```
main.py               — orchestrateur principal
verify_setup.py       — test de connexion Band (lance en premier)
band/client.py        — wrapper REST Band (httpx)
agents/base_agent.py  — base LLM (Groq)
agents/*_agent.py     — logique métier de chaque agent
dashboard/app.py      — Streamlit HITL
ingestion/enricher.py — enrichissement transaction
data/mock_transactions.json — TXN-001/002/003 pour la démo
```
