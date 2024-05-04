import asyncio
import hashlib
import enum
import json
import logging

import pydantic
import pydantic_settings
import uvicorn

from uuid import UUID, uuid4

from fastapi import FastAPI, Header
from starlette.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

from prs.Entity.entity import Room, Player, PlayerChoice, RoomState
from prs.manager import RoomManager

app = FastAPI()


manager = RoomManager()


@app.post("/create_room")
async def create_room(name: str, req_players: int) -> Room:
    new_room: Room = manager.create_room(name, req_players)
    return new_room


class RoomEvent(enum.Enum):
    ConnectedToRoom = "ConnectedToRoom"
    NewPlayerConnected = "NewPlayerConnected"
    PlayerDisconnected = "PlayerDisconnected"
    GameCanBeStart = "GameCanBeStart"
    Draw = "Draw"
    Win = "Win"
    Lose = "Lose"


class RoomEventMessage(pydantic.BaseModel):
    event: RoomEvent
    room: Room


@app.websocket("/start/{room_id}")
async def websocket_connect_room(websocket: WebSocket, room_id: UUID, name: str, player_hash: str | None = None):
    room = None
    player = None
    try:
        await websocket.accept()

        room = manager.get_room(room_id)

        if not room or room.state != RoomState.WaitingPlayers:
            await websocket.close(1003, reason="room net")
            return

        other_players_websocket = manager.get_room_websockets(room)

        player = manager.get_player(player_hash) if player_hash else None

        if not player:
            player = Player(name=name)
            player_hash = manager.add_player(player, room, websocket)

        await websocket.send_text(json.dumps({
            "event": RoomEvent.ConnectedToRoom.value,
            "room": room.model_dump(mode="json"),
            "hash": player_hash,
        }))

        for other_player_websocket in other_players_websocket:
            await other_player_websocket.send_text(json.dumps({
                "event": RoomEvent.NewPlayerConnected.value,
                "room": room.model_dump(mode="json"),
            }))

        while not room.can_start:
            await asyncio.sleep(.3)

        while room.can_start:
            room.state = RoomState.WaitingChoices

            await websocket.send_text(json.dumps({
                "event": RoomEvent.GameCanBeStart.value,
                "room": room.model_dump(mode="json"),
            }))

            while not room.all_players_make_choice:
                player_input = await websocket.receive_text()

                try:
                    player.choice = PlayerChoice(player_input)
                except ValueError:
                    await websocket.send_text(f"not valid choice")

                await asyncio.sleep(.3)

            winners = room.winners
            for room_player in room.players:
                room_player_websocket = manager.get_player_websocket(room_player)

                if room_player in winners:
                    if len(winners) == len(room.players):
                        await room_player_websocket.send_text(json.dumps({
                            "event": RoomEvent.Draw.value,
                            "room": room.model_dump(mode="json"),
                        }))
                    else:
                        await room_player_websocket.send_text(json.dumps({
                            "event": RoomEvent.Win.value,
                            "room": room.model_dump(mode="json"),
                            }))
                else:
                    await room_player_websocket.send_text(json.dumps({
                        "event": RoomEvent.Lose.value,
                        "room": room.model_dump(mode="json"),
                    }))

            for room_player in room.players:
                room_player.choice = None

    except WebSocketDisconnect:
        print(websocket.application_state)
        print(websocket.client_state)
        if websocket.application_state == WebSocketState.CONNECTED and websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1003, reason="konec")
        if room and len(room.players) < room.required_players + 1:
            room.state = RoomState.WaitingPlayers
            if player:
                manager.delete_player(player, room)


app.add_middleware(
    CORSMiddleware,
    allow_origins=("http://localhost:5173", "http://localhost:8080"),
    allow_credentials=True,
    allow_methods=("POST", "GET",),
    allow_headers=("*",)
)

if __name__ == '__main__':
    uvicorn.run("prs.main2:app", port=7000, log_level='info')
