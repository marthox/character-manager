# src/adapters/inbound/routers/characters.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from adapters.inbound.schemas import (
    CharacterCreate,
    CharacterModuleCreate,
    CharacterModuleResponse,
    CharacterModuleUpdate,
    CharacterResponse,
    CharacterUpdate,
)
from adapters.outbound.db.character_repo import SQLCharacterRepository
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
from adapters.outbound.db.session import get_db
from domain.models.character import Character
from domain.models.character_module import CharacterModule
from domain.models.field_definition import FieldType

router = APIRouter(prefix="/characters", tags=["characters"])


def _get_repo(db: Session = Depends(get_db)) -> SQLCharacterRepository:
    return SQLCharacterRepository(db)


def _to_response(char: Character) -> CharacterResponse:
    return CharacterResponse(
        id=char.id,
        player=char.player,
        name=char.name,
        template_id=char.template_id,
        modules=[
            CharacterModuleResponse(id=m.id, definition_id=m.definition_id, values=m.values)
            for m in char.modules
        ],
    )


def _default_values_for_module(mod_def) -> dict:
    result = {}
    for f in mod_def.fields:
        if f.default is not None:
            result[f.name] = f.default
        elif f.field_type == FieldType.LIST:
            result[f.name] = []
        elif f.field_type in (FieldType.INTEGER, FieldType.FLOAT):
            result[f.name] = 0
        elif f.field_type == FieldType.BOOLEAN:
            result[f.name] = False
        else:
            result[f.name] = ""
    return result


@router.get("", response_model=list[CharacterResponse])
def list_characters(
    player: str | None = Query(default=None),
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    if player:
        return [_to_response(c) for c in repo.list_by_player(player)]
    return [_to_response(c) for c in repo.list_all()]


@router.post("", response_model=CharacterResponse, status_code=201)
def create_character(
    body: CharacterCreate,
    repo: SQLCharacterRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    modules: list[CharacterModule] = []

    if body.template_id:
        tmpl_repo = SQLSheetTemplateRepository(db)
        mod_repo = SQLModuleDefinitionRepository(db)
        tmpl = tmpl_repo.get_by_id(body.template_id)
        if tmpl is None:
            raise HTTPException(404, "Template not found")
        for def_id in tmpl.modules:
            mod_def = mod_repo.get_by_id(def_id)
            if mod_def:
                modules.append(
                    CharacterModule(
                        definition_id=def_id,
                        values=_default_values_for_module(mod_def),
                    )
                )

    char = Character(
        player=body.player,
        name=body.name,
        template_id=body.template_id,
        modules=modules,
    )
    repo.save(char)
    return _to_response(char)


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(character_id: str, repo: SQLCharacterRepository = Depends(_get_repo)):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    return _to_response(char)


@router.patch("/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: str,
    body: CharacterUpdate,
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    updated = Character(
        player=body.player if body.player is not None else char.player,
        name=body.name if body.name is not None else char.name,
        template_id=char.template_id,
        modules=char.modules,
    )
    updated.__pydantic_private__["_id"] = char.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.delete("/{character_id}", status_code=204)
def delete_character(character_id: str, repo: SQLCharacterRepository = Depends(_get_repo)):
    if not repo.delete(character_id):
        raise HTTPException(404, "Character not found")


@router.get("/{character_id}/modules", response_model=list[CharacterModuleResponse])
def list_character_modules(
    character_id: str, repo: SQLCharacterRepository = Depends(_get_repo)
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    return [CharacterModuleResponse(id=m.id, definition_id=m.definition_id, values=m.values) for m in char.modules]


@router.post("/{character_id}/modules", response_model=CharacterModuleResponse, status_code=201)
def add_module_to_character(
    character_id: str,
    body: CharacterModuleCreate,
    repo: SQLCharacterRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")

    mod_repo = SQLModuleDefinitionRepository(db)
    mod_def = mod_repo.get_by_id(body.definition_id)
    if mod_def is None:
        raise HTTPException(404, "Module definition not found")

    existing_cats = {
        mod_repo.get_by_id(m.definition_id).category
        for m in char.modules
        if mod_repo.get_by_id(m.definition_id) is not None
    }
    if mod_def.category in existing_cats:
        raise HTTPException(
            409, f"Character already has a module in category '{mod_def.category}'"
        )

    new_mod = CharacterModule(definition_id=body.definition_id, values=body.values)
    updated = Character(
        player=char.player,
        name=char.name,
        template_id=char.template_id,
        modules=char.modules + [new_mod],
    )
    updated.__pydantic_private__["_id"] = char.__pydantic_private__["_id"]
    repo.save(updated)
    return CharacterModuleResponse(id=new_mod.id, definition_id=new_mod.definition_id, values=new_mod.values)


@router.get("/{character_id}/modules/{module_id}", response_model=CharacterModuleResponse)
def get_character_module(
    character_id: str,
    module_id: str,
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    mod = next((m for m in char.modules if m.id == module_id), None)
    if mod is None:
        raise HTTPException(404, "Module not found on character")
    return CharacterModuleResponse(id=mod.id, definition_id=mod.definition_id, values=mod.values)


@router.patch("/{character_id}/modules/{module_id}", response_model=CharacterModuleResponse)
def update_character_module(
    character_id: str,
    module_id: str,
    body: CharacterModuleUpdate,
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    mod = next((m for m in char.modules if m.id == module_id), None)
    if mod is None:
        raise HTTPException(404, "Module not found on character")

    updated_mod = CharacterModule(definition_id=mod.definition_id, values=body.values)
    updated_mod.__pydantic_private__["_id"] = mod.__pydantic_private__["_id"]
    new_modules = [updated_mod if m.id == module_id else m for m in char.modules]
    updated_char = Character(
        player=char.player,
        name=char.name,
        template_id=char.template_id,
        modules=new_modules,
    )
    updated_char.__pydantic_private__["_id"] = char.__pydantic_private__["_id"]
    repo.save(updated_char)
    return CharacterModuleResponse(id=updated_mod.id, definition_id=updated_mod.definition_id, values=updated_mod.values)


@router.delete("/{character_id}/modules/{module_id}", status_code=204)
def remove_character_module(
    character_id: str,
    module_id: str,
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    mod = next((m for m in char.modules if m.id == module_id), None)
    if mod is None:
        raise HTTPException(404, "Module not found on character")
    updated = Character(
        player=char.player,
        name=char.name,
        template_id=char.template_id,
        modules=[m for m in char.modules if m.id != module_id],
    )
    updated.__pydantic_private__["_id"] = char.__pydantic_private__["_id"]
    repo.save(updated)
