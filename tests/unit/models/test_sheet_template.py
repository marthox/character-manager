import pytest
from domain.models.sheet_template import SheetTemplate


def test_sheet_template_creation():
    template = SheetTemplate(name="D&D 5e Base", system="D&D 5e")
    assert template.name == "D&D 5e Base"
    assert template.system == "D&D 5e"
    assert template.modules == []


def test_sheet_template_has_uuid():
    template = SheetTemplate(name="D&D 5e Base", system="D&D 5e")
    assert len(template.id) == 36


def test_two_templates_have_different_ids():
    a = SheetTemplate(name="D&D 5e Base", system="D&D 5e")
    b = SheetTemplate(name="D&D 5e Base", system="D&D 5e")
    assert a.id != b.id


def test_sheet_template_with_modules():
    ids = ["uuid-1", "uuid-2", "uuid-3"]
    template = SheetTemplate(name="D&D 5e Base", system="D&D 5e", modules=ids)
    assert template.modules == ids


def test_sheet_template_modules_preserve_order():
    ids = ["c", "a", "b"]
    template = SheetTemplate(name="Test", system="Test", modules=ids)
    assert template.modules == ["c", "a", "b"]
