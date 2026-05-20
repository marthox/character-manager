from typing import Any
from enum import Enum
from pydantic import BaseModel


class FieldType(str, Enum):
    INTEGER = "integer"
    STRING = "string"
    BOOLEAN = "boolean"
    FLOAT = "float"
    LIST = "list"


class FieldDefinition(BaseModel):
    name: str
    field_type: FieldType
    required: bool = True
    default: Any = None
