import os
from typing import Callable


class Room:
    """Wrapper autour d'une Band room."""

    def __init__(self, sdk_room):
        self._room = sdk_room

    def post_message(self, message: dict) -> None:
        # TODO: adapter selon l'API Band SDK réelle
        self._room.send(message)

    def get_messages(self, since: str | None = None) -> list[dict]:
        # TODO: adapter selon l'API Band SDK réelle
        messages = self._room.history(since=since) if since else self._room.history()
        return [m.content for m in messages]

    def on_message(self, callback: Callable[[dict], None]) -> None:
        # TODO: adapter selon l'API Band SDK réelle
        self._room.subscribe(callback)


class BandClient:
    """Point d'entrée unique pour toutes les interactions Band."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ["BAND_API_KEY"]
        # TODO: initialiser le vrai client Band SDK ici
        # from band_sdk import BandClient as _BandClient
        # self._client = _BandClient(api_key=self._api_key)

    def join_room(self, room_id: str) -> Room:
        # TODO: adapter selon l'API Band SDK réelle
        raise NotImplementedError("Compléter après lecture des docs Band SDK")

    def post_to_escalations(self, case_id: str, verdict: str, summary: str) -> None:
        room = self.join_room("escalations")
        room.post_message({"case_id": case_id, "verdict": verdict, "summary": summary})
