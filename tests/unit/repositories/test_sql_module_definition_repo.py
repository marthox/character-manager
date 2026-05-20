import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adapters.outbound.db.models import Base, ModuleDefinitionORM
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from domain.models.module_definition import ModuleDefinition
from domain.models.field_definition import FieldDefinition, FieldType


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def repo(db_session):
    return SQLModuleDefinitionRepository(db_session)


@pytest.fixture(autouse=True)
def clear_table(db_session):
    yield
    db_session.query(ModuleDefinitionORM).delete()
    db_session.commit()


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
    repo.save(hp_module)
    retrieved = repo.get_by_id(hp_module.id)
    assert retrieved is not None
    assert retrieved.id == hp_module.id
    assert retrieved.name == "D&D 5e Hit Points"
    assert retrieved.category == "health"
    assert len(retrieved.fields) == 2


def test_get_by_id_returns_none_when_not_found(repo):
    assert repo.get_by_id("nonexistent") is None


def test_list_all_empty(repo):
    assert repo.list_all() == []


def test_list_all_returns_saved(repo, hp_module):
    xp = ModuleDefinition(name="XP", category="experience", fields=[])
    repo.save(hp_module)
    repo.save(xp)
    all_mods = repo.list_all()
    assert len(all_mods) == 2
    ids = {m.id for m in all_mods}
    assert hp_module.id in ids
    assert xp.id in ids


def test_save_same_object_twice_is_idempotent(repo, hp_module):
    repo.save(hp_module)
    repo.save(hp_module)
    assert len(repo.list_all()) == 1


def test_delete_existing(repo, hp_module):
    repo.save(hp_module)
    assert repo.delete(hp_module.id) is True
    assert repo.get_by_id(hp_module.id) is None


def test_delete_nonexistent_returns_false(repo):
    assert repo.delete("nonexistent") is False


def test_fields_round_trip(repo, hp_module):
    repo.save(hp_module)
    retrieved = repo.get_by_id(hp_module.id)
    assert retrieved.fields[0].name == "max_hp"
    assert retrieved.fields[0].field_type == FieldType.INTEGER
    assert retrieved.fields[0].default == 10
