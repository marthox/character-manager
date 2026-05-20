import re
from pydantic import field_validator
from domain.models.base_class import BaseClass
from domain.models.field_definition import FieldDefinition


class ModuleDefinition(BaseClass):
    name: str
    description: str | None = None
    category: str
    fields: list[FieldDefinition] = []

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        normalized = v.lower().strip()
        if not re.match(r"^[a-z][a-z0-9_]*$", normalized):
            raise ValueError(
                f"Category '{normalized}' is invalid. "
                "Must start with a letter and contain only lowercase letters, digits, or underscores."
            )
        return normalized
