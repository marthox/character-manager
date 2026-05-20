from abc import ABC, abstractmethod
from domain.models.sheet_template import SheetTemplate


class SheetTemplateRepository(ABC):
    @abstractmethod
    def save(self, template: SheetTemplate) -> SheetTemplate:
        """Persist a sheet template and return it."""

    @abstractmethod
    def get_by_id(self, template_id: str) -> SheetTemplate | None:
        """Return a sheet template by id, or None if not found."""

    @abstractmethod
    def list_all(self) -> list[SheetTemplate]:
        """Return all sheet templates."""

    @abstractmethod
    def delete(self, template_id: str) -> bool:
        """Delete a sheet template. Returns True if deleted, False if not found."""
