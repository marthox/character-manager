from domain.models.sheet_template import SheetTemplate
from domain.ports.outbound.sheet_template_repository import SheetTemplateRepository


class InMemorySheetTemplateRepository(SheetTemplateRepository):
    def __init__(self):
        self._store: dict[str, SheetTemplate] = {}

    def save(self, template: SheetTemplate) -> SheetTemplate:
        self._store[template.id] = template
        return template

    def get_by_id(self, template_id: str) -> SheetTemplate | None:
        return self._store.get(template_id)

    def list_all(self) -> list[SheetTemplate]:
        return list(self._store.values())

    def delete(self, template_id: str) -> bool:
        if template_id not in self._store:
            return False
        del self._store[template_id]
        return True
