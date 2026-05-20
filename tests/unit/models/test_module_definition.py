import pytest
from domain.models.module_definition import ModuleDefinition
from domain.models.field_definition import FieldDefinition, FieldType


def test_module_definition_creation():
    mod = ModuleDefinition(name="D&D 5e Hit Points", category="health", fields=[])
    assert mod.name == "D&D 5e Hit Points"
    assert mod.category == "health"
    assert mod.fields == []
    assert mod.description is None


def test_module_definition_has_uuid():
    mod = ModuleDefinition(name="HP", category="health", fields=[])
    assert len(mod.id) == 36
    assert mod.id.count("-") == 4


def test_two_module_definitions_have_different_ids():
    a = ModuleDefinition(name="HP", category="health", fields=[])
    b = ModuleDefinition(name="HP", category="health", fields=[])
    assert a.id != b.id


def test_module_definition_category_normalized_to_lowercase():
    mod = ModuleDefinition(name="HP", category="Health", fields=[])
    assert mod.category == "health"


def test_module_definition_category_strips_whitespace():
    mod = ModuleDefinition(name="HP", category="  health  ", fields=[])
    assert mod.category == "health"


def test_module_definition_category_with_underscores():
    mod = ModuleDefinition(name="Death Saves", category="death_saves", fields=[])
    assert mod.category == "death_saves"


def test_module_definition_category_with_digits():
    mod = ModuleDefinition(name="Alt", category="health2", fields=[])
    assert mod.category == "health2"


def test_module_definition_category_must_start_with_letter():
    with pytest.raises(ValueError, match="invalid"):
        ModuleDefinition(name="Bad", category="1health", fields=[])


def test_module_definition_category_rejects_special_chars():
    with pytest.raises(ValueError, match="invalid"):
        ModuleDefinition(name="Bad", category="health-points", fields=[])


def test_module_definition_category_rejects_spaces():
    with pytest.raises(ValueError, match="invalid"):
        ModuleDefinition(name="Bad", category="health points", fields=[])


def test_module_definition_with_fields():
    mod = ModuleDefinition(
        name="D&D 5e Hit Points",
        category="health",
        fields=[
            FieldDefinition(name="max_hp", field_type=FieldType.INTEGER, default=10),
            FieldDefinition(name="current_hp", field_type=FieldType.INTEGER, default=10),
            FieldDefinition(name="temp_hp", field_type=FieldType.INTEGER, default=0),
        ],
    )
    assert len(mod.fields) == 3
    assert mod.fields[0].name == "max_hp"


def test_module_definition_with_description():
    mod = ModuleDefinition(
        name="HP", category="health", description="Tracks hit points", fields=[]
    )
    assert mod.description == "Tracks hit points"
