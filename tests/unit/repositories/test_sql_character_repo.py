import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adapters.outbound.db.models import Base, CharacterORM, CharacterModuleORM
from adapters.outbound.db.character_repo import SQLCharacterRepository
from domain.models.character import Character
from domain.models.character_module import CharacterModule


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
    return SQLCharacterRepository(db_session)


@pytest.fixture(autouse=True)
def clear_tables(db_session):
    yield
    db_session.query(CharacterModuleORM).delete()
    db_session.query(CharacterORM).delete()
    db_session.commit()


@pytest.fixture
def aragorn():
    return Character(
        player="player-1",
        name="Aragorn",
        modules=[
            CharacterModule(
                definition_id="health-id",
                values={"max_hp": 90, "current_hp": 90, "temp_hp": 0},
            )
        ],
    )


@pytest.fixture
def legolas():
    return Character(player="player-1", name="Legolas")


@pytest.fixture
def gandalf():
    return Character(player="player-2", name="Gandalf")


def test_save_and_get_by_id(repo, aragorn):
    repo.save(aragorn)
    retrieved = repo.get_by_id(aragorn.id)
    assert retrieved is not None
    assert retrieved.id == aragorn.id
    assert retrieved.name == "Aragorn"
    assert len(retrieved.modules) == 1
    assert retrieved.modules[0].values["max_hp"] == 90


def test_get_by_id_returns_none_when_not_found(repo):
    assert repo.get_by_id("nonexistent") is None


def test_list_all_empty(repo):
    assert repo.list_all() == []


def test_list_all_returns_all_saved(repo, aragorn, gandalf):
    repo.save(aragorn)
    repo.save(gandalf)
    assert len(repo.list_all()) == 2


def test_list_by_player(repo, aragorn, legolas, gandalf):
    repo.save(aragorn)
    repo.save(legolas)
    repo.save(gandalf)
    p1 = repo.list_by_player("player-1")
    assert len(p1) == 2
    assert {c.name for c in p1} == {"Aragorn", "Legolas"}


def test_list_by_player_empty_for_unknown(repo, aragorn):
    repo.save(aragorn)
    assert repo.list_by_player("unknown") == []


def test_delete_existing(repo, aragorn):
    repo.save(aragorn)
    assert repo.delete(aragorn.id) is True
    assert repo.get_by_id(aragorn.id) is None


def test_delete_cascades_to_modules(repo, aragorn, db_session):
    repo.save(aragorn)
    repo.delete(aragorn.id)
    modules = db_session.query(CharacterModuleORM).filter_by(character_id=aragorn.id).all()
    assert modules == []


def test_delete_nonexistent_returns_false(repo):
    assert repo.delete("nonexistent") is False


def test_module_values_round_trip(repo, aragorn):
    repo.save(aragorn)
    retrieved = repo.get_by_id(aragorn.id)
    mod = retrieved.modules[0]
    assert mod.definition_id == "health-id"
    assert mod.values == {"max_hp": 90, "current_hp": 90, "temp_hp": 0}
