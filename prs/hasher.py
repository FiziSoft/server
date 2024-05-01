import hashlib

import pydantic_settings

from prs.Entity.entity import Player


class HashingSettings(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_prefix="HASHING_", case_sensitive=False)
    salt: str


class PlayerTokenizer:
    def __init__(self):
        self._settings = HashingSettings()

    def generate_token(self, player: Player) -> str:
        salted_player_id = str(player.id) + self._settings.salt

        return hashlib.sha256(salted_player_id.encode()).hexdigest()
