# tests/integration/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adapters.outbound.db.models import Base
from adapters.outbound.db.session import get_db
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
from domain.seeder import seed_dnd5e
from main import app

TEST_DATABASE_URL = "sqlite:///./test_integration.db"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    import os
    try:
        os.remove("test_integration.db")
    except FileNotFoundError:
        pass


@pytest.fixture(scope="session")
def seeded_db(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    seed_dnd5e(SQLModuleDefinitionRepository(session), SQLSheetTemplateRepository(session))
    session.commit()
    session.close()


@pytest.fixture(scope="function")
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session, seeded_db):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()
