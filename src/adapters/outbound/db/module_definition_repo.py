from uuid import UUID
from sqlalchemy.orm import Session

from adapters.outbound.db.models import ModuleDefinitionORM
from domain.models.field_definition import FieldDefinition
from domain.models.module_definition import ModuleDefinition
from domain.ports.outbound.module_definition_repository import ModuleDefinitionRepository


def _to_domain(orm: ModuleDefinitionORM) -> ModuleDefinition:
    mod = ModuleDefinition(
        name=orm.name,
        description=orm.description,
        category=orm.category,
        fields=[FieldDefinition(**f) for f in (orm.fields or [])],
    )
    mod.__pydantic_private__["_id"] = UUID(orm.id)
    return mod


class SQLModuleDefinitionRepository(ModuleDefinitionRepository):
    def __init__(self, session: Session):
        self._session = session

    def save(self, module: ModuleDefinition) -> ModuleDefinition:
        existing = self._session.get(ModuleDefinitionORM, module.id)
        if existing:
            existing.name = module.name
            existing.description = module.description
            existing.category = module.category
            existing.fields = [f.model_dump() for f in module.fields]
        else:
            self._session.add(
                ModuleDefinitionORM(
                    id=module.id,
                    name=module.name,
                    description=module.description,
                    category=module.category,
                    fields=[f.model_dump() for f in module.fields],
                )
            )
        self._session.commit()
        return module

    def get_by_id(self, module_id: str) -> ModuleDefinition | None:
        orm = self._session.get(ModuleDefinitionORM, module_id)
        return _to_domain(orm) if orm else None

    def list_all(self) -> list[ModuleDefinition]:
        return [_to_domain(o) for o in self._session.query(ModuleDefinitionORM).all()]

    def delete(self, module_id: str) -> bool:
        orm = self._session.get(ModuleDefinitionORM, module_id)
        if orm is None:
            return False
        self._session.delete(orm)
        self._session.commit()
        return True
