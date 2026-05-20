import pytest
from domain.models.character_module import CharacterModule


def test_character_module_has_uuid():
    mod = CharacterModule(definition_id="some-def-id", values={})
    assert len(mod.id) == 36
    assert mod.id.count("-") == 4


def test_two_character_modules_have_different_ids():
    a = CharacterModule(definition_id="id-1")
    b = CharacterModule(definition_id="id-2")
    assert a.id != b.id


def test_character_module_stores_values():
    mod = CharacterModule(
        definition_id="health-def-id",
        values={"max_hp": 45, "current_hp": 30, "temp_hp": 0},
    )
    assert mod.values["max_hp"] == 45
    assert mod.values["current_hp"] == 30
    assert mod.values["temp_hp"] == 0


def test_character_module_default_empty_values():
    mod = CharacterModule(definition_id="some-id")
    assert mod.values == {}


def test_character_module_stores_string_values():
    mod = CharacterModule(
        definition_id="identity-def-id",
        values={"race": "Elf", "class": "Wizard", "alignment": "Neutral Good"},
    )
    assert mod.values["race"] == "Elf"


def test_character_module_stores_list_values():
    mod = CharacterModule(
        definition_id="proficiencies-def-id",
        values={"languages": ["Common", "Elvish", "Dwarvish"]},
    )
    assert mod.values["languages"] == ["Common", "Elvish", "Dwarvish"]
