# src/adapters/inbound/schemas.py
from typing import Any
from pydantic import BaseModel
from domain.models.field_definition import FieldType


# ── Field / Module Definition ────────────────────────────────────────────────

class FieldDefinitionSchema(BaseModel):
    name: str
    field_type: FieldType
    required: bool = True
    default: Any = None


class ModuleDefinitionCreate(BaseModel):
    name: str
    description: str | None = None
    category: str
    fields: list[FieldDefinitionSchema] = []


class ModuleDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    fields: list[FieldDefinitionSchema] | None = None


class ModuleDefinitionResponse(BaseModel):
    id: str
    name: str
    description: str | None
    category: str
    fields: list[FieldDefinitionSchema]


# ── Sheet Template ────────────────────────────────────────────────────────────

class SheetTemplateCreate(BaseModel):
    name: str
    system: str


class SheetTemplateUpdate(BaseModel):
    name: str | None = None
    system: str | None = None


class TemplateAddModule(BaseModel):
    definition_id: str


class TemplateReorderModules(BaseModel):
    module_ids: list[str]


class SheetTemplateResponse(BaseModel):
    id: str
    name: str
    system: str
    modules: list[str]


# ── Character ─────────────────────────────────────────────────────────────────

class CharacterCreate(BaseModel):
    player: str
    name: str | None = None
    template_id: str | None = None


class CharacterUpdate(BaseModel):
    name: str | None = None
    player: str | None = None


class CharacterModuleCreate(BaseModel):
    definition_id: str
    values: dict[str, Any] = {}


class CharacterModuleUpdate(BaseModel):
    values: dict[str, Any]


class CharacterModuleResponse(BaseModel):
    id: str
    definition_id: str
    values: dict[str, Any]


class CharacterResponse(BaseModel):
    id: str
    player: str
    name: str | None
    template_id: str | None
    modules: list[CharacterModuleResponse]
