from uuid import UUID
from sqlalchemy.orm import Session

from adapters.outbound.db.models import CharacterORM, CharacterModuleORM
from domain.models.character import Character
from domain.models.character_module import CharacterModule
from domain.ports.outbound.character_repository import CharacterRepository


def _module_to_domain(orm: CharacterModuleORM) -> CharacterModule:
    mod = CharacterModule(
        definition_id=orm.definition_id,
        values=dict(orm.values or {}),
    )
    mod.__pydantic_private__["_id"] = UUID(orm.id)
    return mod


def _to_domain(orm: CharacterORM) -> Character:
    char = Character(
        player=orm.player,
        name=orm.name,
        template_id=orm.template_id,
        modules=[_module_to_domain(m) for m in orm.modules],
    )
    char.__pydantic_private__["_id"] = UUID(orm.id)
    return char


class SQLCharacterRepository(CharacterRepository):
    def __init__(self, session: Session):
        self._session = session

    def save(self, character: Character) -> Character:
        existing = self._session.get(CharacterORM, character.id)
        if existing:
            existing.player = character.player
            existing.name = character.name
            existing.template_id = character.template_id
            # Replace all character modules
            for m in list(existing.modules):
                self._session.delete(m)
            self._session.flush()
            for mod in character.modules:
                existing.modules.append(
                    CharacterModuleORM(
                        id=mod.id,
                        character_id=character.id,
                        definition_id=mod.definition_id,
                        values=dict(mod.values),
                    )
                )
        else:
            orm = CharacterORM(
                id=character.id,
                player=character.player,
                name=character.name,
                template_id=character.template_id,
                modules=[
                    CharacterModuleORM(
                        id=mod.id,
                        character_id=character.id,
                        definition_id=mod.definition_id,
                        values=dict(mod.values),
                    )
                    for mod in character.modules
                ],
            )
            self._session.add(orm)
        self._session.commit()
        return character

    def get_by_id(self, character_id: str) -> Character | None:
        orm = self._session.get(CharacterORM, character_id)
        return _to_domain(orm) if orm else None

    def list_by_player(self, player_id: str) -> list[Character]:
        orms = self._session.query(CharacterORM).filter_by(player=player_id).all()
        return [_to_domain(o) for o in orms]

    def list_all(self) -> list[Character]:
        return [_to_domain(o) for o in self._session.query(CharacterORM).all()]

    def delete(self, character_id: str) -> bool:
        orm = self._session.get(CharacterORM, character_id)
        if orm is None:
            return False
        self._session.delete(orm)
        self._session.commit()
        return True
