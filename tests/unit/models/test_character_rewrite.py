import pytest
from domain.models.character import Character
from domain.models.character_module import CharacterModule


def test_character_creation_minimal():
    char = Character(player="player-uuid")
    assert char.player == "player-uuid"
    assert char.name is None
    assert char.template_id is None
    assert char.modules == []


def test_character_has_uuid():
    char = Character(player="player-uuid")
    assert len(char.id) == 36


def test_two_characters_have_different_ids():
    a = Character(player="player-uuid")
    b = Character(player="player-uuid")
    assert a.id != b.id


def test_character_with_name():
    char = Character(player="player-uuid", name="Aragorn")
    assert char.name == "Aragorn"


def test_character_with_template():
    char = Character(player="player-uuid", template_id="dnd5e-template-id")
    assert char.template_id == "dnd5e-template-id"


def test_character_with_modules():
    hp_module = CharacterModule(
        definition_id="health-def-id",
        values={"max_hp": 45, "current_hp": 45, "temp_hp": 0},
    )
    char = Character(player="player-uuid", name="Legolas", modules=[hp_module])
    assert len(char.modules) == 1
    assert char.modules[0].values["max_hp"] == 45


def test_character_modules_preserve_order():
    mod_a = CharacterModule(definition_id="health-id", values={})
    mod_b = CharacterModule(definition_id="experience-id", values={})
    mod_c = CharacterModule(definition_id="attributes-id", values={})
    char = Character(player="player-uuid", modules=[mod_a, mod_b, mod_c])
    assert char.modules[0].definition_id == "health-id"
    assert char.modules[1].definition_id == "experience-id"
    assert char.modules[2].definition_id == "attributes-id"
