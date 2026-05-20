from abc import ABC, abstractmethod
from domain.models.module_definition import ModuleDefinition


class ModuleDefinitionRepository(ABC):
    @abstractmethod
    def save(self, module: ModuleDefinition) -> ModuleDefinition:
        """Persist a module definition and return it."""

    @abstractmethod
    def get_by_id(self, module_id: str) -> ModuleDefinition | None:
        """Return a module definition by id, or None if not found."""

    @abstractmethod
    def list_all(self) -> list[ModuleDefinition]:
        """Return all module definitions."""

    @abstractmethod
    def delete(self, module_id: str) -> bool:
        """Delete a module definition. Returns True if deleted, False if not found."""
