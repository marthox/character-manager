import pytest
from domain.models.sheet_template import SheetTemplate
from adapters.outbound.memory.sheet_template_repo import InMemorySheetTemplateRepository


@pytest.fixture
def repo():
    return InMemorySheetTemplateRepository()


@pytest.fixture
def dnd_template():
    return SheetTemplate(
        name="D&D 5e Base",
        system="D&D 5e",
        modules=["health-id", "experience-id", "attributes-id"],
    )


def test_save_and_get_by_id(repo, dnd_template):
    repo.save(dnd_template)
    retrieved = repo.get_by_id(dnd_template.id)
    assert retrieved is not None
    assert retrieved.name == "D&D 5e Base"
    assert retrieved.modules == ["health-id", "experience-id", "attributes-id"]


def test_get_by_id_returns_none_when_not_found(repo):
    assert repo.get_by_id("nonexistent-id") is None


def test_list_all_empty(repo):
    assert repo.list_all() == []


def test_list_all_returns_all_saved(repo, dnd_template):
    pf_template = SheetTemplate(name="Pathfinder 2e Base", system="Pathfinder 2e")
    repo.save(dnd_template)
    repo.save(pf_template)
    all_templates = repo.list_all()
    assert len(all_templates) == 2


def test_delete_existing(repo, dnd_template):
    repo.save(dnd_template)
    result = repo.delete(dnd_template.id)
    assert result is True
    assert repo.get_by_id(dnd_template.id) is None


def test_delete_nonexistent_returns_false(repo):
    assert repo.delete("nonexistent-id") is False


def test_each_repo_instance_is_independent():
    repo_a = InMemorySheetTemplateRepository()
    repo_b = InMemorySheetTemplateRepository()
    template = SheetTemplate(name="D&D 5e Base", system="D&D 5e")
    repo_a.save(template)
    assert repo_b.get_by_id(template.id) is None
