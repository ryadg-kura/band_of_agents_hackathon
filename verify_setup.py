"""
verify_setup.py — Validate Band connectivity for all Quorum agents.

Usage:
    python verify_setup.py

Checks per agent:
  1. Credentials loaded from agent_config.yaml
  2. GET /agent/me  →  connection OK + agent handle
  3. (synthesis-agent only) POST test message to room "quorum-test"

Exit code 0 if all agents pass, 1 if any fail.
"""

import json
import os
import sys

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "agent_config.yaml")
REST_URL = os.getenv("THENVOI_REST_URL", "https://app.band.ai").rstrip("/")
API_BASE = f"{REST_URL}/api/v1"

AGENTS = ["aml-agent", "sanctions-agent", "fraud-agent", "synthesis-agent"]
PLACEHOLDER = "COLLE_UUID_ICI"

# ANSI colours — fall back gracefully on non-TTY
_TTY = sys.stdout.isatty()
GREEN  = "\033[92m" if _TTY else ""
RED    = "\033[91m" if _TTY else ""
YELLOW = "\033[93m" if _TTY else ""
BOLD   = "\033[1m"  if _TTY else ""
RESET  = "\033[0m"  if _TTY else ""

OK   = f"{GREEN}✓{RESET}"
FAIL = f"{RED}✗{RESET}"
WARN = f"{YELLOW}!{RESET}"


def _header(text: str) -> None:
    print(f"\n{BOLD}{text}{RESET}")
    print("─" * len(text))


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def check_agent(name: str, config: dict) -> bool:
    """Run all checks for one agent. Returns True if all pass."""
    _header(name)
    entry = config.get(name, {})
    agent_id = entry.get("agent_id", "")
    api_key  = entry.get("api_key", "")

    # 1 — credentials present and not placeholder
    if not agent_id or agent_id == PLACEHOLDER:
        print(f"  {FAIL} agent_id manquant ou placeholder")
        return False
    if not api_key or api_key == PLACEHOLDER:
        print(f"  {FAIL} api_key manquante ou placeholder")
        return False
    print(f"  {OK} Credentials chargés  agent_id={agent_id}")

    # 2 — GET /agent/me
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    try:
        r = httpx.get(f"{API_BASE}/agent/me", headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        handle = (
            data.get("handle")
            or data.get("name")
            or data.get("agent", {}).get("handle")
            or "N/A"
        )
        print(f"  {OK} Connexion Band OK    handle={handle}")
    except httpx.HTTPStatusError as e:
        print(f"  {FAIL} HTTP {e.response.status_code}: {e.response.text[:120]}")
        return False
    except Exception as e:
        print(f"  {FAIL} Erreur réseau: {e}")
        return False

    return True


def post_test_message(config: dict) -> bool:
    """Create a 'quorum-test' room and post a test message as synthesis-agent."""
    _header("Test message → room 'quorum-test'")

    entry  = config.get("synthesis-agent", {})
    api_key = entry.get("api_key", "")
    if not api_key or api_key == PLACEHOLDER:
        print(f"  {WARN} synthesis-agent non configuré — test message ignoré")
        return True

    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    # Create (or reuse) test room via POST /agent/chats
    try:
        # Reuse the room from the local cache if already created
        cache: dict[str, str] = {}
        try:
            with open(os.path.join(os.path.dirname(__file__), ".band_room_cache.json")) as f:
                cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        chat_id = cache.get("quorum-test")
        if chat_id:
            print(f"  {OK} Room existante (cache) id={chat_id}")
        else:
            r = httpx.post(
                f"{API_BASE}/agent/chats",
                headers=headers,
                json={"chat": {}},
                timeout=10,
            )
            r.raise_for_status()
            body = r.json()
            chat_id = body.get("data", {}).get("id") or body.get("id")
            cache["quorum-test"] = chat_id
            cache_path = os.path.join(os.path.dirname(__file__), ".band_room_cache.json")
            with open(cache_path, "w") as f:
                json.dump(cache, f, indent=2)
            print(f"  {OK} Room créée             id={chat_id}")

    except Exception as e:
        print(f"  {FAIL} Impossible de créer la room: {e}")
        return False

    # Post test message
    try:
        payload = {
            "type": "verify_setup",
            "message": "Quorum connectivity test OK",
            "agents": AGENTS,
        }
        r = httpx.post(
            f"{API_BASE}/agent/chats/{chat_id}/events",
            headers=headers,
            json={"event": {"content": json.dumps(payload), "message_type": "task", "metadata": {}}},
            timeout=10,
        )
        r.raise_for_status()
        print(f"  {OK} Message test posté dans room 'quorum-test'")
        return True
    except httpx.HTTPStatusError as e:
        print(f"  {FAIL} HTTP {e.response.status_code}: {e.response.text[:120]}")
        return False
    except Exception as e:
        print(f"  {FAIL} Erreur: {e}")
        return False


def main() -> int:
    print(f"\n{BOLD}╔══════════════════════════════════════╗")
    print(f"║  Quorum — Band connectivity check    ║")
    print(f"╚══════════════════════════════════════╝{RESET}")
    print(f"  REST: {REST_URL}")

    # Load config
    try:
        config = _load_config()
    except FileNotFoundError:
        print(f"\n{FAIL} agent_config.yaml introuvable à {CONFIG_PATH}")
        print("  Crée-le en copiant agent_config.yaml.example et remplis les clés.")
        return 1
    except yaml.YAMLError as e:
        print(f"\n{FAIL} YAML invalide: {e}")
        return 1

    results: dict[str, bool] = {}
    for agent in AGENTS:
        results[agent] = check_agent(agent, config)

    # Post test message only if synthesis-agent passes
    if results.get("synthesis-agent"):
        results["test-message"] = post_test_message(config)

    # Summary
    _header("Résumé")
    all_ok = True
    for name, ok in results.items():
        icon = OK if ok else FAIL
        print(f"  {icon} {name}")
        if not ok:
            all_ok = False

    if all_ok:
        print(f"\n{GREEN}{BOLD}Tout est OK — prêt pour la démo.{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}Des vérifications ont échoué. Corrige agent_config.yaml.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
