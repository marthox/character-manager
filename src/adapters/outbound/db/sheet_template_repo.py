from uuid import UUID
from sqlalchemy.orm import Session

from adapters.outbound.db.models import SheetTemplateORM
from domain.models.sheet_template import SheetTemplate
from domain.ports.outbound.sheet_template_repository import SheetTemplateRepository


def _to_domain(orm: SheetTemplateORM) -> SheetTemplate:
    tmpl = SheetTemplate(
        name=orm.name,
        system=orm.system,
        modules=list(orm.modules or []),
    )
    tmpl.__pydantic_private__["_id"] = UUID(orm.id)
    return tmpl


class SQLSheetTemplateRepository(SheetTemplateRepository):
    def __init__(self, session: Session):
        self._session = session

    def save(self, template: SheetTemplate) -> SheetTemplate:
        existing = self._session.get(SheetTemplateORM, template.id)
        if existing:
            existing.name = template.name
            existing.system = template.system
            existing.modules = list(template.modules)
        else:
            self._session.add(
                SheetTemplateORM(
                    id=template.id,
                    name=template.name,
                    system=template.system,
                    modules=list(template.modules),
                )
            )
        self._session.commit()
        return template

    def get_by_id(self, template_id: str) -> SheetTemplate | None:
        orm = self._session.get(SheetTemplateORM, template_id)
        return _to_domain(orm) if orm else None

    def list_all(self) -> list[SheetTemplate]:
        return [_to_domain(o) for o in self._session.query(SheetTemplateORM).all()]

    def delete(self, template_id: str) -> bool:
        orm = self._session.get(SheetTemplateORM, template_id)
        if orm is None:
            return False
        self._session.delete(orm)
        self._session.commit()
        return True
