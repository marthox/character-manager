from typing import Any
from domain.models.base_class import BaseClass


class CharacterModule(BaseClass):
    definition_id: str
    values: dict[str, Any] = {}
