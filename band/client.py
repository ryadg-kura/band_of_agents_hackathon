import os
from typing import Callable
import thenvoi


class Room:
    """Wrapper autour d'une Band room."""

    def __init__(self, sdk_room):
        self._room = sdk_room

    def post_message(self, message: dict) -> None:
        # TODO: vérifier le nom exact de la méthode dans les docs thenvoi
        self._room.send(message)

    def get_messages(self, since: str | None = None) -> list[dict]:
        # TODO: vérifier le nom exact de la méthode dans les docs thenvoi
        messages = self._room.history(since=since) if since else self._room.history()
        return [m.content for m in messages]

    def on_message(self, callback: Callable[[dict], None]) -> None:
        # TODO: vérifier le nom exact de la méthode dans les docs thenvoi
        self._room.subscribe(callback)


class BandClient:
    """Point d'entrée unique pour toutes les interactions Band."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ["BAND_API_KEY"]
        # TODO: vérifier le nom exact de la classe dans les docs thenvoi
        self._client = thenvoi.Client(api_key=self._api_key)

    def join_room(self, room_id: str) -> Room:
        # TODO: vérifier le nom exact de la méthode dans les docs thenvoi
        sdk_room = self._client.join_room(room_id)
        return Room(sdk_room)

    def post_to_escalations(self, case_id: str, verdict: str, summary: str) -> None:
        room = self.join_room("escalations")
        room.post_message({"case_id": case_id, "verdict": verdict, "summary": summary})
