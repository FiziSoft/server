import enum
from enum import Enum
from uuid import UUID, uuid4

import pydantic


class PlayerChoice(Enum):
    Rock = "rock"
    Paper = "paper"
    Scissors = "scissors"


class Player (pydantic.BaseModel):
    id: UUID = pydantic.Field(default_factory=uuid4)
    name: pydantic.constr(max_length=20)
    choice: PlayerChoice | None = None
    score: int = 0


class RoomState(enum.Enum):
    WaitingPlayers = "WaitingPlayers"
    WaitingChoices = "WaitingChoices"


class Room(pydantic.BaseModel):
    id: UUID = pydantic.Field(default_factory=uuid4)
    state: RoomState = RoomState.WaitingPlayers
    name: str
    players: list[Player] = pydantic.Field(default_factory=lambda: [])
    required_players: int

    def add_player(self, player: Player) -> None:
        self.players.append(player)

    def reset(self) -> None:
        for i in self.players:
            i.choice = None

    def delete_player(self, player: Player) -> None:
        self.players.remove(player)


    @property
    def can_start(self) -> bool:
        return len(self.players) == self.required_players

    @property
    def all_players_make_choice(self) -> bool:
        return all(i.choice for i in self.players) # делаю цикл из всех игроков єтой комнаті и смотрю что бі уних біл сделан вібор

    @property
    def winners(self) -> list[Player]:
        rock_players = []
        paper_players = []
        scissors_players = []

        for player in self.players:
            if player.choice == PlayerChoice.Rock:
                rock_players.append(player)
            elif player.choice == PlayerChoice.Paper:
                paper_players.append(player)
            elif player.choice == PlayerChoice.Scissors:
                scissors_players.append(player)

        if rock_players and paper_players and scissors_players:
            return self.players

        else:
            if paper_players and not scissors_players:
                winners = paper_players

            elif rock_players and not paper_players:
                winners = rock_players

            elif not rock_players and scissors_players:
                winners = scissors_players
            else:
                winners = []

            for winner in winners:
                winner.score += 1

            return winners
