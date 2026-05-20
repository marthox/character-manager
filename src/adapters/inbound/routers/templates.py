# src/adapters/inbound/routers/templates.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adapters.inbound.schemas import (
    SheetTemplateCreate,
    SheetTemplateResponse,
    SheetTemplateUpdate,
    TemplateAddModule,
    TemplateReorderModules,
)
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
from adapters.outbound.db.character_repo import SQLCharacterRepository
from adapters.outbound.db.session import get_db
from domain.models.sheet_template import SheetTemplate

router = APIRouter(prefix="/templates", tags=["templates"])


def _get_repo(db: Session = Depends(get_db)) -> SQLSheetTemplateRepository:
    return SQLSheetTemplateRepository(db)


def _to_response(t: SheetTemplate) -> SheetTemplateResponse:
    return SheetTemplateResponse(id=t.id, name=t.name, system=t.system, modules=t.modules)


@router.get("", response_model=list[SheetTemplateResponse])
def list_templates(repo: SQLSheetTemplateRepository = Depends(_get_repo)):
    return [_to_response(t) for t in repo.list_all()]


@router.post("", response_model=SheetTemplateResponse, status_code=201)
def create_template(
    body: SheetTemplateCreate,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
):
    template = SheetTemplate(name=body.name, system=body.system)
    repo.save(template)
    return _to_response(template)


@router.get("/{template_id}", response_model=SheetTemplateResponse)
def get_template(template_id: str, repo: SQLSheetTemplateRepository = Depends(_get_repo)):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    return _to_response(t)


@router.patch("/{template_id}", response_model=SheetTemplateResponse)
def update_template(
    template_id: str,
    body: SheetTemplateUpdate,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    updated = SheetTemplate(
        name=body.name if body.name is not None else t.name,
        system=body.system if body.system is not None else t.system,
        modules=t.modules,
    )
    updated.__pydantic_private__["_id"] = t.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: str,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")

    char_repo = SQLCharacterRepository(db)
    for c in char_repo.list_all():
        if c.template_id == template_id:
            raise HTTPException(409, "Template is referenced by a character")

    repo.delete(template_id)


@router.post("/{template_id}/modules", response_model=SheetTemplateResponse)
def add_module_to_template(
    template_id: str,
    body: TemplateAddModule,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")

    mod_repo = SQLModuleDefinitionRepository(db)
    mod_def = mod_repo.get_by_id(body.definition_id)
    if mod_def is None:
        raise HTTPException(404, "Module definition not found")

    existing_cats = {
        mod_repo.get_by_id(def_id).category
        for def_id in t.modules
        if mod_repo.get_by_id(def_id) is not None
    }
    if mod_def.category in existing_cats:
        raise HTTPException(409, f"Template already has a module in category '{mod_def.category}'")

    updated = SheetTemplate(
        name=t.name,
        system=t.system,
        modules=t.modules + [body.definition_id],
    )
    updated.__pydantic_private__["_id"] = t.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.delete("/{template_id}/modules/{definition_id}", response_model=SheetTemplateResponse)
def remove_module_from_template(
    template_id: str,
    definition_id: str,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    if definition_id not in t.modules:
        raise HTTPException(404, "Module not in template")

    updated = SheetTemplate(
        name=t.name,
        system=t.system,
        modules=[m for m in t.modules if m != definition_id],
    )
    updated.__pydantic_private__["_id"] = t.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.patch("/{template_id}/modules/order", response_model=SheetTemplateResponse)
def reorder_template_modules(
    template_id: str,
    body: TemplateReorderModules,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    if set(body.module_ids) != set(t.modules):
        raise HTTPException(422, "module_ids must contain exactly the same IDs as the template's modules")

    updated = SheetTemplate(name=t.name, system=t.system, modules=body.module_ids)
    updated.__pydantic_private__["_id"] = t.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)
