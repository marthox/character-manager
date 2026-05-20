import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adapters.outbound.db.models import Base, SheetTemplateORM
from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
from domain.models.sheet_template import SheetTemplate


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
    return SQLSheetTemplateRepository(db_session)


@pytest.fixture(autouse=True)
def clear_table(db_session):
    yield
    db_session.query(SheetTemplateORM).delete()
    db_session.commit()


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
    assert retrieved.id == dnd_template.id
    assert retrieved.name == "D&D 5e Base"
    assert retrieved.system == "D&D 5e"
    assert retrieved.modules == ["health-id", "experience-id", "attributes-id"]


def test_get_by_id_returns_none_when_not_found(repo):
    assert repo.get_by_id("nonexistent") is None


def test_list_all_empty(repo):
    assert repo.list_all() == []


def test_list_all_returns_all_saved(repo, dnd_template):
    pf = SheetTemplate(name="Pathfinder 2e", system="Pathfinder 2e")
    repo.save(dnd_template)
    repo.save(pf)
    assert len(repo.list_all()) == 2


def test_delete_existing(repo, dnd_template):
    repo.save(dnd_template)
    assert repo.delete(dnd_template.id) is True
    assert repo.get_by_id(dnd_template.id) is None


def test_delete_nonexistent_returns_false(repo):
    assert repo.delete("nonexistent") is False


def test_modules_order_preserved(repo, dnd_template):
    repo.save(dnd_template)
    retrieved = repo.get_by_id(dnd_template.id)
    assert retrieved.modules == ["health-id", "experience-id", "attributes-id"]
