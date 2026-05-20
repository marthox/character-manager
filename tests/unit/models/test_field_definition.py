import pytest
from domain.models.field_definition import FieldType, FieldDefinition


def test_field_type_values():
    assert FieldType.INTEGER == "integer"
    assert FieldType.STRING == "string"
    assert FieldType.BOOLEAN == "boolean"
    assert FieldType.FLOAT == "float"
    assert FieldType.LIST == "list"


def test_field_definition_minimal():
    field = FieldDefinition(name="hp", field_type=FieldType.INTEGER)
    assert field.name == "hp"
    assert field.field_type == FieldType.INTEGER
    assert field.required is True
    assert field.default is None


def test_field_definition_with_default():
    field = FieldDefinition(name="level", field_type=FieldType.INTEGER, default=1)
    assert field.default == 1


def test_field_definition_optional_field():
    field = FieldDefinition(name="notes", field_type=FieldType.STRING, required=False, default="")
    assert field.required is False
    assert field.default == ""


def test_field_definition_boolean_type():
    field = FieldDefinition(name="is_alive", field_type=FieldType.BOOLEAN, default=True)
    assert field.default is True


def test_field_definition_list_type():
    field = FieldDefinition(name="languages", field_type=FieldType.LIST, default=[])
    assert field.field_type == FieldType.LIST
