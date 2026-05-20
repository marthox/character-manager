from domain.models.base_class import BaseClass
from domain.models.character_module import CharacterModule


class Character(BaseClass):
    player: str
    name: str | None = None
    template_id: str | None = None
    modules: list[CharacterModule] = []
