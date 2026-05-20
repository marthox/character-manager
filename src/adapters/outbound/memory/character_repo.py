from domain.models.character import Character
from domain.ports.outbound.character_repository import CharacterRepository


class InMemoryCharacterRepository(CharacterRepository):
    def __init__(self):
        self._store: dict[str, Character] = {}

    def save(self, character: Character) -> Character:
        self._store[character.id] = character
        return character

    def get_by_id(self, character_id: str) -> Character | None:
        return self._store.get(character_id)

    def list_by_player(self, player_id: str) -> list[Character]:
        return [c for c in self._store.values() if c.player == player_id]

    def list_all(self) -> list[Character]:
        return list(self._store.values())

    def delete(self, character_id: str) -> bool:
        if character_id not in self._store:
            return False
        del self._store[character_id]
        return True
