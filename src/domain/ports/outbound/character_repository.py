from abc import ABC, abstractmethod
from domain.models.character import Character


class CharacterRepository(ABC):
    @abstractmethod
    def save(self, character: Character) -> Character:
        """Persist a character and return it."""

    @abstractmethod
    def get_by_id(self, character_id: str) -> Character | None:
        """Return a character by id, or None if not found."""

    @abstractmethod
    def list_by_player(self, player_id: str) -> list[Character]:
        """Return all characters belonging to a player."""

    @abstractmethod
    def list_all(self) -> list[Character]:
        """Return all characters."""

    @abstractmethod
    def delete(self, character_id: str) -> bool:
        """Delete a character. Returns True if deleted, False if not found."""
