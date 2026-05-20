import pytest
from domain.models.module_definition import ModuleDefinition
from domain.models.field_definition import FieldDefinition, FieldType
from adapters.outbound.memory.module_definition_repo import InMemoryModuleDefinitionRepository


@pytest.fixture
def repo():
    return InMemoryModuleDefinitionRepository()


@pytest.fixture
def hp_module():
    return ModuleDefinition(
        name="D&D 5e Hit Points",
        category="health",
        fields=[
            FieldDefinition(name="max_hp", field_type=FieldType.INTEGER, default=10),
            FieldDefinition(name="current_hp", field_type=FieldType.INTEGER, default=10),
        ],
    )


def test_save_and_get_by_id(repo, hp_module):
    saved = repo.save(hp_module)
    retrieved = repo.get_by_id(saved.id)
    assert retrieved is not None
    assert retrieved.id == hp_module.id
    assert retrieved.name == "D&D 5e Hit Points"


def test_get_by_id_returns_none_when_not_found(repo):
    assert repo.get_by_id("nonexistent-id") is None


def test_list_all_empty(repo):
    assert repo.list_all() == []


def test_list_all_returns_all_saved(repo, hp_module):
    xp_module = ModuleDefinition(name="D&D 5e Experience", category="experience", fields=[])
    repo.save(hp_module)
    repo.save(xp_module)
    all_modules = repo.list_all()
    assert len(all_modules) == 2
    ids = {m.id for m in all_modules}
    assert hp_module.id in ids
    assert xp_module.id in ids


def test_delete_existing(repo, hp_module):
    repo.save(hp_module)
    result = repo.delete(hp_module.id)
    assert result is True
    assert repo.get_by_id(hp_module.id) is None


def test_delete_nonexistent_returns_false(repo):
    assert repo.delete("nonexistent-id") is False


def test_save_same_object_twice_does_not_duplicate(repo, hp_module):
    repo.save(hp_module)
    repo.save(hp_module)
    assert len(repo.list_all()) == 1


def test_each_repo_instance_is_independent():
    repo_a = InMemoryModuleDefinitionRepository()
    repo_b = InMemoryModuleDefinitionRepository()
    mod = ModuleDefinition(name="HP", category="health", fields=[])
    repo_a.save(mod)
    assert repo_b.get_by_id(mod.id) is None
