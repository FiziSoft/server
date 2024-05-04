from uuid import UUID

from starlette.websockets import WebSocket

from prs.Entity.entity import Room, Player
from prs.hasher import PlayerTokenizer


class RoomManager:
    def __init__(self):
        self._rooms: dict[UUID, Room] = {}
        self._tokenizer = PlayerTokenizer()
        self._player_websockets: dict[UUID, WebSocket] = {}
        self._hashed_players: dict[str, Player] = {}

    def create_room(self, name: str, req_players: int) -> Room:
        current_room = Room(name=name, required_players=req_players)
        self._rooms[current_room.id] = current_room

        return current_room

    def get_room(self, room_id: UUID) -> Room | None:
        return self._rooms.get(room_id, None)

    def get_room_websockets(self, room: Room) -> list[WebSocket]:
        return [self._player_websockets[player.id] for player in room.players]

    def get_player(self, player_hash: str) -> Player | None:
        return self._hashed_players.get(player_hash, None)

    def get_player_websocket(self, player: Player) -> WebSocket:
        return self._player_websockets[player.id]

    def add_player(self, player: Player, room: Room, websocket: WebSocket) -> str:
        player_hash = self._tokenizer.generate_token(player)
        self._player_websockets[player.id] = websocket
        self._hashed_players[player_hash] = player
        room.add_player(player)

        return player_hash

    def delete_player(self, player: Player, room: Room) -> None:
        player_hash = self._tokenizer.generate_token(player)
        self._player_websockets.pop(player.id)
        self._hashed_players.pop(player_hash)
        room.delete_player(player)


