from domain.models.module_definition import ModuleDefinition
from domain.ports.outbound.module_definition_repository import ModuleDefinitionRepository


class InMemoryModuleDefinitionRepository(ModuleDefinitionRepository):
    def __init__(self):
        self._store: dict[str, ModuleDefinition] = {}

    def save(self, module: ModuleDefinition) -> ModuleDefinition:
        self._store[module.id] = module
        return module

    def get_by_id(self, module_id: str) -> ModuleDefinition | None:
        return self._store.get(module_id)

    def list_all(self) -> list[ModuleDefinition]:
        return list(self._store.values())

    def delete(self, module_id: str) -> bool:
        if module_id not in self._store:
            return False
        del self._store[module_id]
        return True
