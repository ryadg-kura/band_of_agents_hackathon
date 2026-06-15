"""
Band REST client for Quorum.

Uses agent credentials from agent_config.yaml to call the Band REST API.
Room IDs are resolved on first use and cached in .band_room_cache.json.

Environment variables required:
  THENVOI_REST_URL  — Band REST base URL (default: https://app.band.ai)
  THENVOI_WS_URL    — WebSocket URL (default: wss://app.band.ai/api/v1/socket/websocket)
"""

import json
import os
import threading
import time
from typing import Callable

import httpx
import yaml
from dotenv import load_dotenv

load_dotenv()

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_ROOT, "agent_config.yaml")
_ROOM_CACHE_PATH = os.path.join(_ROOT, ".band_room_cache.json")

REST_URL = os.getenv("THENVOI_REST_URL", "https://app.band.ai").rstrip("/")
API_BASE = f"{REST_URL}/api/v1"


def load_agent_config(agent_name: str) -> tuple[str, str]:
    """Return (agent_id, api_key) for a named agent from agent_config.yaml."""
    with open(_CONFIG_PATH) as f:
        config = yaml.safe_load(f)
    entry = config[agent_name]
    return entry["agent_id"], entry["api_key"]


class Room:
    """Wrapper for a Band chat room identified by its UUID."""

    def __init__(self, chat_id: str, headers: dict) -> None:
        self._id = chat_id
        self._headers = headers

    def post_message(self, message: dict | str) -> dict:
        """POST structured data to the room via the events endpoint (no mentions needed)."""
        content = json.dumps(message) if isinstance(message, dict) else str(message)
        with httpx.Client(headers=self._headers, timeout=30) as http:
            r = http.post(
                f"{API_BASE}/agent/chats/{self._id}/events",
                json={"event": {"content": content, "message_type": "task", "metadata": {}}},
            )
            r.raise_for_status()
            return r.json()

    def get_messages(self) -> list[dict]:
        """GET full conversation history via /context. JSON content is parsed."""
        with httpx.Client(headers=self._headers, timeout=30) as http:
            r = http.get(f"{API_BASE}/agent/chats/{self._id}/context")
            r.raise_for_status()

        # Response: {"data": [...], "meta": {...}}
        items: list = r.json().get("data") or []
        result = []
        for item in items:
            raw = item.get("content") or ""
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                parsed = {"type": "text", "content": raw}
            # Attach Band metadata so dashboard can display sender info
            parsed.setdefault("_sender", item.get("sender_name"))
            parsed.setdefault("_at", item.get("inserted_at"))
            result.append(parsed)
        return result

    def on_message(self, callback: Callable[[dict], None]) -> None:
        """Poll for new messages every 3 s in a daemon thread."""
        seen: set[str] = set()

        def _loop() -> None:
            while True:
                try:
                    for msg in self.get_messages():
                        key = json.dumps(msg, sort_keys=True)
                        if key not in seen:
                            seen.add(key)
                            callback(msg)
                except Exception:
                    pass
                time.sleep(3)

        threading.Thread(target=_loop, daemon=True).start()

    # Alias used by dashboard
    listen = on_message


class BandClient:
    """
    Orchestrator-level Band client (defaults to synthesis-agent credentials).

    Room names (e.g. "escalations", "case-TXN-001") are resolved to Band chat
    UUIDs on first use and persisted to .band_room_cache.json so subsequent
    runs avoid extra API calls. Pre-configure IDs in agent_config.yaml under
    a `rooms:` key to skip the lookup/creation step entirely.
    """

    def __init__(self, agent_name: str = "synthesis-agent") -> None:
        self.agent_id, self.api_key = load_agent_config(agent_name)
        self._headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        self._room_cache: dict[str, str] = self._load_room_cache()

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def _load_room_cache(self) -> dict[str, str]:
        cache: dict[str, str] = {}
        # 1. Rooms pre-configured in agent_config.yaml
        try:
            with open(_CONFIG_PATH) as f:
                config = yaml.safe_load(f)
            if isinstance(config.get("rooms"), dict):
                cache.update(config["rooms"])
        except (FileNotFoundError, KeyError, TypeError):
            pass
        # 2. Rooms created at runtime (persisted locally)
        try:
            with open(_ROOM_CACHE_PATH) as f:
                cache.update(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return cache

    def _save_room_cache(self) -> None:
        with open(_ROOM_CACHE_PATH, "w") as f:
            json.dump(self._room_cache, f, indent=2)

    # ------------------------------------------------------------------
    # Room resolution
    # ------------------------------------------------------------------

    def _create_room(self, room_name: str) -> str:
        """Create a new Band chat room and return its ID."""
        with httpx.Client(headers=self._headers, timeout=30) as http:
            r = http.post(f"{API_BASE}/agent/chats", json={"chat": {}})
            r.raise_for_status()

        # Response: {"data": {"id": "...", ...}}
        body = r.json()
        chat_id = body.get("data", {}).get("id") or body.get("id")
        if not chat_id:
            raise RuntimeError(f"Cannot extract chat ID from Band response: {body}")
        return chat_id

    def join_room(self, room_name: str) -> Room:
        """Return a Room for the given name, creating the chat if needed."""
        if room_name not in self._room_cache:
            chat_id = self._create_room(room_name)
            self._room_cache[room_name] = chat_id
            self._save_room_cache()
        return Room(self._room_cache[room_name], self._headers)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def post_to_escalations(self, case_id: str, verdict: str, summary: str) -> None:
        self.join_room("escalations").post_message(
            {"type": "escalation", "case_id": case_id, "verdict": verdict, "summary": summary}
        )

    def validate_connection(self) -> dict:
        """GET /agent/me — verify credentials and return agent profile."""
        with httpx.Client(headers=self._headers, timeout=30) as http:
            r = http.get(f"{API_BASE}/agent/me")
            r.raise_for_status()
            return r.json()
