# src/adapters/inbound/routers/modules.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adapters.inbound.schemas import (
    ModuleDefinitionCreate,
    ModuleDefinitionResponse,
    ModuleDefinitionUpdate,
)
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.session import get_db
from domain.models.field_definition import FieldDefinition
from domain.models.module_definition import ModuleDefinition

router = APIRouter(prefix="/modules", tags=["modules"])


def _get_repo(db: Session = Depends(get_db)) -> SQLModuleDefinitionRepository:
    return SQLModuleDefinitionRepository(db)


def _to_response(mod: ModuleDefinition) -> ModuleDefinitionResponse:
    return ModuleDefinitionResponse(
        id=mod.id,
        name=mod.name,
        description=mod.description,
        category=mod.category,
        fields=[f.model_dump() for f in mod.fields],
    )


@router.get("", response_model=list[ModuleDefinitionResponse])
def list_modules(repo: SQLModuleDefinitionRepository = Depends(_get_repo)):
    return [_to_response(m) for m in repo.list_all()]


@router.post("", response_model=ModuleDefinitionResponse, status_code=201)
def create_module(
    body: ModuleDefinitionCreate,
    repo: SQLModuleDefinitionRepository = Depends(_get_repo),
):
    mod = ModuleDefinition(
        name=body.name,
        description=body.description,
        category=body.category,
        fields=[FieldDefinition(**f.model_dump()) for f in body.fields],
    )
    repo.save(mod)
    return _to_response(mod)


@router.get("/{module_id}", response_model=ModuleDefinitionResponse)
def get_module(
    module_id: str,
    repo: SQLModuleDefinitionRepository = Depends(_get_repo),
):
    mod = repo.get_by_id(module_id)
    if mod is None:
        raise HTTPException(404, "Module definition not found")
    return _to_response(mod)


@router.patch("/{module_id}", response_model=ModuleDefinitionResponse)
def update_module(
    module_id: str,
    body: ModuleDefinitionUpdate,
    repo: SQLModuleDefinitionRepository = Depends(_get_repo),
):
    mod = repo.get_by_id(module_id)
    if mod is None:
        raise HTTPException(404, "Module definition not found")
    updated = ModuleDefinition(
        name=body.name if body.name is not None else mod.name,
        description=body.description if body.description is not None else mod.description,
        category=mod.category,
        fields=[FieldDefinition(**f.model_dump()) for f in body.fields] if body.fields is not None else mod.fields,
    )
    updated.__pydantic_private__["_id"] = mod.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.delete("/{module_id}", status_code=204)
def delete_module(
    module_id: str,
    repo: SQLModuleDefinitionRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    mod = repo.get_by_id(module_id)
    if mod is None:
        raise HTTPException(404, "Module definition not found")

    from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
    template_repo = SQLSheetTemplateRepository(db)
    for t in template_repo.list_all():
        if module_id in t.modules:
            raise HTTPException(409, "Module is used by a template")

    from adapters.outbound.db.character_repo import SQLCharacterRepository
    char_repo = SQLCharacterRepository(db)
    for c in char_repo.list_all():
        if any(m.definition_id == module_id for m in c.modules):
            raise HTTPException(409, "Module is used by a character")

    repo.delete(module_id)
