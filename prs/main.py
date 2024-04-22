import asyncio
import enum

import pydantic
import uvicorn

from uuid import UUID, uuid4

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

from prs.Entity.entity import Room, Player, PlayerChoice

app = FastAPI()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []  # после : указіваю тип

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket, code: int, reason: str | None = None):
        self.active_connections.remove(websocket)
        await websocket.close(code, reason)

    @staticmethod
    async def send_personal_message(message: str, websocket: WebSocket):
        await websocket.send_text(message)
    # async def broadcast(self, message: str):
    #     for connection in self.active_connections:
    #         await connection.send_text(message)


class RoomsManager: # отвечает за связь комнаты с интерфейсом(апи/методов работы с сервером)
    def __init__(self):
        self.rooms: dict[UUID, Room] = {}  #создаю пустое множество(колекцию) комнат с типом Словарь у которого ключ ююайди == ююайди комнаті
        self.players_and_websocket: dict[UUID, WebSocket] = {}

    def create(self, name: str, req_players: int) -> Room:
        current_room = Room(id=uuid4(), name=name, required_players=req_players)
        self.rooms[current_room.id] = current_room
        return current_room

    def get_room(self, room_id: UUID) -> Room | None:
        return self.rooms.get(room_id, None)    #get принимает два значения 1 получает по первому если нет то что во втором параметре

    def register_player(self, player: Player, websocket: WebSocket) -> None:
        self.players_and_websocket[player.id] = websocket

    def get_websockets_for_room(self, room: Room) -> list[WebSocket]:
        '''Возвращаем вебсокеты всех игроков, которые находятся в комнате'''
        return [self.players_and_websocket[player.id] for player in room.players]


room_manager = RoomsManager()  #создание обькта класса идет со скобками


@app.post("/create_room")
async def create_room(name: str, req_players: int) -> Room:
    new_room: Room = room_manager.create(name, req_players)
    return new_room


manager = ConnectionManager()


class RoomEvent(enum.Enum):
    ConnectedToRoom = "ConnectedToRoom"
    NewPlayerConnected = "NewPlayerConnected"
    PlayerDisconnected = "PlayerDisconnected"


class RoomEventMessage(pydantic.BaseModel):
    event: RoomEvent
    room: Room


async def send_room_event_message(websocket: WebSocket, room: Room, event: RoomEvent) -> None:
    await websocket.send_text(RoomEventMessage(event=event, room=room).model_dump_json())


@app.websocket("/start/{room_id}")
async def websocket_connect_room(websocket: WebSocket, room_id: UUID, name: str):
    await manager.connect(websocket)

    try:
        room = room_manager.get_room(room_id)
        if not room:
            await manager.disconnect(websocket, 1003, reason="room net")
            return

        other_players_websocket = room_manager.get_websockets_for_room(room)

        player = Player(name=name)
        room.add_player(player)
        room_manager.register_player(player, websocket)

        await send_room_event_message(websocket, room, RoomEvent.ConnectedToRoom)

        for other_player_websocket in other_players_websocket:
            await send_room_event_message(other_player_websocket, room, RoomEvent.NewPlayerConnected)

        while True:
            if room.can_start:  # когда подключилось заданое количество игроков
                await manager.send_personal_message("Game can be started", websocket)
                if room.all_players_make_choice:
                    await manager.send_personal_message("YouGetChoice", websocket) #когда все сделали ход
                    if player in room.winners:
                        if len(room.winners) == len(room.players):
                            await manager.send_personal_message("Draw", websocket)
                        else:
                            await manager.send_personal_message("You Win", websocket)
                            player.score += 1
                    else:
                        await manager.send_personal_message("You Lose", websocket)

                    room.reset()

                player_input = await websocket.receive_text()
                try:
                    player.choice = PlayerChoice(player_input)
                except ValueError:
                    await manager.send_personal_message(f"not valid choice", websocket)
            await asyncio.sleep(0.3)
            # await manager.broadcast(f"Client #{client_id} says: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket, 1003, reason="konec")
        # await manager.broadcast(f"Client #{client_id} left the chat")


# @app.websocket("/ws")
# async def websocket_endpoint(websocket: WebSocket, room_id: UUID | None = None):
#     await manager.connect(websocket)
#     try:
#         # if not room_id:
#         #     new_room = room_manager.create()
#         while True:
#             data = await websocket.receive_text()
#
#             # new_room = room_manager.create()
#             await manager.send_personal_message(f"You wrote: {new_room.id}", websocket)
#             # await manager.broadcast(f"Client #{client_id} says: {data}")
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)
#         # await manager.broadcast(f"Client #{client_id} left the chat")


app.add_middleware(
    CORSMiddleware,
    allow_origins=("http://localhost:5173", "http://localhost:8080"),
    allow_credentials=True,
    allow_methods=("POST", "GET",),
    allow_headers=("*",)
)

if __name__ == '__main__':
    uvicorn.run("prs.main:app", port=7000, log_level='info')
