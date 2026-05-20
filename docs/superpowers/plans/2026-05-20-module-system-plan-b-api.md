# Character Sheet Module System — Plan B: API, Database, and Seeding

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the domain layer (Plan A) to a real PostgreSQL database, expose the full REST API from the spec, seed D&D 5e modules and template at startup, and produce a production-ready service runnable via `docker-compose up`.

**Architecture:** SQLAlchemy 2.0 (sync) + psycopg2 for DB access. FastAPI routers with Pydantic schemas for HTTP. Repositories take a `Session` injected via FastAPI `Depends`. Lifespan creates tables and runs idempotent seeder.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0, psycopg2-binary, Pydantic v2, pytest, httpx (TestClient), Docker / PostgreSQL 17

---

## File Map

### Create
| File | Purpose |
|------|---------|
| `src/adapters/outbound/db/__init__.py` | Package marker |
| `src/adapters/outbound/db/models.py` | SQLAlchemy ORM table definitions |
| `src/adapters/outbound/db/session.py` | Engine, `SessionLocal`, `get_db()` dependency |
| `src/adapters/outbound/db/module_definition_repo.py` | `SQLModuleDefinitionRepository` |
| `src/adapters/outbound/db/sheet_template_repo.py` | `SQLSheetTemplateRepository` |
| `src/adapters/outbound/db/character_repo.py` | `SQLCharacterRepository` |
| `src/adapters/inbound/schemas.py` | All Pydantic request/response schemas |
| `src/adapters/inbound/routers/__init__.py` | Package marker |
| `src/adapters/inbound/routers/modules.py` | `/modules` CRUD routes |
| `src/adapters/inbound/routers/templates.py` | `/templates` routes + module management |
| `src/adapters/inbound/routers/characters.py` | `/characters` routes + character module management |
| `src/domain/seeder.py` | Idempotent D&D 5e seeder |
| `tests/integration/__init__.py` | Package marker |
| `tests/integration/conftest.py` | TestClient + SQLite override |
| `tests/integration/test_golden_paths.py` | End-to-end golden path tests |

### Rewrite
| File | Change |
|------|--------|
| `src/main.py` | Full app wiring: lifespan, routers, DI |

### Delete
```
src/adapters/outbound/db.py          ← empty stub
src/adapters/inbound/api.py          ← old placeholder
src/adapters/inbound/user.py         ← old placeholder
```

---

## Task 1: Dependencies + ORM models + DB session

**Files:**
- Modify: `pyproject.toml`
- Create: `src/adapters/outbound/db/__init__.py`
- Create: `src/adapters/outbound/db/models.py`
- Create: `src/adapters/outbound/db/session.py`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Replace the `dependencies` and `[dependency-groups]` sections:

```toml
dependencies = [
    "fastapi[standard]>=0.116.1",
    "sqlalchemy>=2.0.44",
    "psycopg2-binary>=2.9",
]

[dependency-groups]
dev = [
    "pylint>=3.3.8",
    "pytest>=8.4.1",
    "httpx>=0.28",
]
```

- [ ] **Step 2: Sync dependencies**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv sync
```

Expected: lock file updated, no errors.

- [ ] **Step 3: Create ORM models**

```python
# src/adapters/outbound/db/models.py
from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ModuleDefinitionORM(Base):
    __tablename__ = "module_definitions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=False, index=True)
    fields = Column(JSON, nullable=False, default=list)


class SheetTemplateORM(Base):
    __tablename__ = "sheet_templates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    system = Column(String, nullable=False)
    modules = Column(JSON, nullable=False, default=list)


class CharacterORM(Base):
    __tablename__ = "characters"

    id = Column(String, primary_key=True)
    player = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    template_id = Column(String, nullable=True)
    modules = relationship(
        "CharacterModuleORM",
        back_populates="character",
        cascade="all, delete-orphan",
    )


class CharacterModuleORM(Base):
    __tablename__ = "character_modules"

    id = Column(String, primary_key=True)
    character_id = Column(String, ForeignKey("characters.id"), nullable=False, index=True)
    definition_id = Column(String, nullable=False)
    values = Column(JSON, nullable=False, default=dict)
    character = relationship("CharacterORM", back_populates="modules")
```

- [ ] **Step 4: Create DB session module**

```python
# src/adapters/outbound/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dev.db")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5: Create package marker**

Create an empty `src/adapters/outbound/db/__init__.py`.

- [ ] **Step 6: Verify imports**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run python -c "
from adapters.outbound.db.models import Base, ModuleDefinitionORM, SheetTemplateORM, CharacterORM, CharacterModuleORM
from adapters.outbound.db.session import engine, SessionLocal, get_db
print('DB layer imported successfully')
"
```

Expected: `DB layer imported successfully`

- [ ] **Step 7: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add pyproject.toml uv.lock src/adapters/outbound/db/ && git commit -m "feat: add SQLAlchemy ORM models and DB session setup"
```

---

## Task 2: DB ModuleDefinition repository

**Files:**
- Create: `src/adapters/outbound/db/module_definition_repo.py`
- Create: `tests/unit/repositories/test_sql_module_definition_repo.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/repositories/test_sql_module_definition_repo.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adapters.outbound.db.models import Base
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
    db_session.query(__import__("adapters.outbound.db.models", fromlist=["ModuleDefinitionORM"]).ModuleDefinitionORM).delete()
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


def test_save_updates_existing(repo, hp_module):
    repo.save(hp_module)
    # Simulate update by mutating via ORM directly, then re-save domain object
    # (domain model is immutable so we test that save is idempotent)
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_sql_module_definition_repo.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.outbound.db.module_definition_repo'`

- [ ] **Step 3: Create the implementation**

```python
# src/adapters/outbound/db/module_definition_repo.py
from uuid import UUID
from sqlalchemy.orm import Session

from adapters.outbound.db.models import ModuleDefinitionORM
from domain.models.field_definition import FieldDefinition
from domain.models.module_definition import ModuleDefinition
from domain.ports.outbound.module_definition_repository import ModuleDefinitionRepository


def _to_domain(orm: ModuleDefinitionORM) -> ModuleDefinition:
    mod = ModuleDefinition(
        name=orm.name,
        description=orm.description,
        category=orm.category,
        fields=[FieldDefinition(**f) for f in (orm.fields or [])],
    )
    mod.__pydantic_private__["_id"] = UUID(orm.id)
    return mod


class SQLModuleDefinitionRepository(ModuleDefinitionRepository):
    def __init__(self, session: Session):
        self._session = session

    def save(self, module: ModuleDefinition) -> ModuleDefinition:
        existing = self._session.get(ModuleDefinitionORM, module.id)
        if existing:
            existing.name = module.name
            existing.description = module.description
            existing.category = module.category
            existing.fields = [f.model_dump() for f in module.fields]
        else:
            self._session.add(
                ModuleDefinitionORM(
                    id=module.id,
                    name=module.name,
                    description=module.description,
                    category=module.category,
                    fields=[f.model_dump() for f in module.fields],
                )
            )
        self._session.commit()
        return module

    def get_by_id(self, module_id: str) -> ModuleDefinition | None:
        orm = self._session.get(ModuleDefinitionORM, module_id)
        return _to_domain(orm) if orm else None

    def list_all(self) -> list[ModuleDefinition]:
        return [_to_domain(o) for o in self._session.query(ModuleDefinitionORM).all()]

    def delete(self, module_id: str) -> bool:
        orm = self._session.get(ModuleDefinitionORM, module_id)
        if orm is None:
            return False
        self._session.delete(orm)
        self._session.commit()
        return True
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_sql_module_definition_repo.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/outbound/db/module_definition_repo.py tests/unit/repositories/test_sql_module_definition_repo.py && git commit -m "feat: add SQL ModuleDefinition repository"
```

---

## Task 3: DB SheetTemplate repository

**Files:**
- Create: `src/adapters/outbound/db/sheet_template_repo.py`
- Create: `tests/unit/repositories/test_sql_sheet_template_repo.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/repositories/test_sql_sheet_template_repo.py
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_sql_sheet_template_repo.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.outbound.db.sheet_template_repo'`

- [ ] **Step 3: Create the implementation**

```python
# src/adapters/outbound/db/sheet_template_repo.py
from uuid import UUID
from sqlalchemy.orm import Session

from adapters.outbound.db.models import SheetTemplateORM
from domain.models.sheet_template import SheetTemplate
from domain.ports.outbound.sheet_template_repository import SheetTemplateRepository


def _to_domain(orm: SheetTemplateORM) -> SheetTemplate:
    tmpl = SheetTemplate(
        name=orm.name,
        system=orm.system,
        modules=list(orm.modules or []),
    )
    tmpl.__pydantic_private__["_id"] = UUID(orm.id)
    return tmpl


class SQLSheetTemplateRepository(SheetTemplateRepository):
    def __init__(self, session: Session):
        self._session = session

    def save(self, template: SheetTemplate) -> SheetTemplate:
        existing = self._session.get(SheetTemplateORM, template.id)
        if existing:
            existing.name = template.name
            existing.system = template.system
            existing.modules = list(template.modules)
        else:
            self._session.add(
                SheetTemplateORM(
                    id=template.id,
                    name=template.name,
                    system=template.system,
                    modules=list(template.modules),
                )
            )
        self._session.commit()
        return template

    def get_by_id(self, template_id: str) -> SheetTemplate | None:
        orm = self._session.get(SheetTemplateORM, template_id)
        return _to_domain(orm) if orm else None

    def list_all(self) -> list[SheetTemplate]:
        return [_to_domain(o) for o in self._session.query(SheetTemplateORM).all()]

    def delete(self, template_id: str) -> bool:
        orm = self._session.get(SheetTemplateORM, template_id)
        if orm is None:
            return False
        self._session.delete(orm)
        self._session.commit()
        return True
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_sql_sheet_template_repo.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/outbound/db/sheet_template_repo.py tests/unit/repositories/test_sql_sheet_template_repo.py && git commit -m "feat: add SQL SheetTemplate repository"
```

---

## Task 4: DB Character repository

**Files:**
- Create: `src/adapters/outbound/db/character_repo.py`
- Create: `tests/unit/repositories/test_sql_character_repo.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/repositories/test_sql_character_repo.py
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_sql_character_repo.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.outbound.db.character_repo'`

- [ ] **Step 3: Create the implementation**

```python
# src/adapters/outbound/db/character_repo.py
from uuid import UUID
from sqlalchemy.orm import Session

from adapters.outbound.db.models import CharacterORM, CharacterModuleORM
from domain.models.character import Character
from domain.models.character_module import CharacterModule
from domain.ports.outbound.character_repository import CharacterRepository


def _module_to_domain(orm: CharacterModuleORM) -> CharacterModule:
    mod = CharacterModule(
        definition_id=orm.definition_id,
        values=dict(orm.values or {}),
    )
    mod.__pydantic_private__["_id"] = UUID(orm.id)
    return mod


def _to_domain(orm: CharacterORM) -> Character:
    char = Character(
        player=orm.player,
        name=orm.name,
        template_id=orm.template_id,
        modules=[_module_to_domain(m) for m in orm.modules],
    )
    char.__pydantic_private__["_id"] = UUID(orm.id)
    return char


class SQLCharacterRepository(CharacterRepository):
    def __init__(self, session: Session):
        self._session = session

    def save(self, character: Character) -> Character:
        existing = self._session.get(CharacterORM, character.id)
        if existing:
            existing.player = character.player
            existing.name = character.name
            existing.template_id = character.template_id
            # Replace all character modules
            for m in list(existing.modules):
                self._session.delete(m)
            self._session.flush()
            for mod in character.modules:
                existing.modules.append(
                    CharacterModuleORM(
                        id=mod.id,
                        character_id=character.id,
                        definition_id=mod.definition_id,
                        values=dict(mod.values),
                    )
                )
        else:
            orm = CharacterORM(
                id=character.id,
                player=character.player,
                name=character.name,
                template_id=character.template_id,
                modules=[
                    CharacterModuleORM(
                        id=mod.id,
                        character_id=character.id,
                        definition_id=mod.definition_id,
                        values=dict(mod.values),
                    )
                    for mod in character.modules
                ],
            )
            self._session.add(orm)
        self._session.commit()
        return character

    def get_by_id(self, character_id: str) -> Character | None:
        orm = self._session.get(CharacterORM, character_id)
        return _to_domain(orm) if orm else None

    def list_by_player(self, player_id: str) -> list[Character]:
        orms = self._session.query(CharacterORM).filter_by(player=player_id).all()
        return [_to_domain(o) for o in orms]

    def list_all(self) -> list[Character]:
        return [_to_domain(o) for o in self._session.query(CharacterORM).all()]

    def delete(self, character_id: str) -> bool:
        orm = self._session.get(CharacterORM, character_id)
        if orm is None:
            return False
        self._session.delete(orm)
        self._session.commit()
        return True
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_sql_character_repo.py -v
```

Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/outbound/db/character_repo.py tests/unit/repositories/test_sql_character_repo.py && git commit -m "feat: add SQL Character repository"
```

---

## Task 5: API schemas

**Files:**
- Create: `src/adapters/inbound/schemas.py`

No tests at this level — schemas are validated via route handler tests in Tasks 6–8.

- [ ] **Step 1: Create the schemas file**

```python
# src/adapters/inbound/schemas.py
from typing import Any
from pydantic import BaseModel
from domain.models.field_definition import FieldType


# ── Field / Module Definition ────────────────────────────────────────────────

class FieldDefinitionSchema(BaseModel):
    name: str
    field_type: FieldType
    required: bool = True
    default: Any = None


class ModuleDefinitionCreate(BaseModel):
    name: str
    description: str | None = None
    category: str
    fields: list[FieldDefinitionSchema] = []


class ModuleDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    fields: list[FieldDefinitionSchema] | None = None


class ModuleDefinitionResponse(BaseModel):
    id: str
    name: str
    description: str | None
    category: str
    fields: list[FieldDefinitionSchema]


# ── Sheet Template ────────────────────────────────────────────────────────────

class SheetTemplateCreate(BaseModel):
    name: str
    system: str


class SheetTemplateUpdate(BaseModel):
    name: str | None = None
    system: str | None = None


class TemplateAddModule(BaseModel):
    definition_id: str


class TemplateReorderModules(BaseModel):
    module_ids: list[str]


class SheetTemplateResponse(BaseModel):
    id: str
    name: str
    system: str
    modules: list[str]


# ── Character ─────────────────────────────────────────────────────────────────

class CharacterCreate(BaseModel):
    player: str
    name: str | None = None
    template_id: str | None = None


class CharacterUpdate(BaseModel):
    name: str | None = None
    player: str | None = None


class CharacterModuleCreate(BaseModel):
    definition_id: str
    values: dict[str, Any] = {}


class CharacterModuleUpdate(BaseModel):
    values: dict[str, Any]


class CharacterModuleResponse(BaseModel):
    id: str
    definition_id: str
    values: dict[str, Any]


class CharacterResponse(BaseModel):
    id: str
    player: str
    name: str | None
    template_id: str | None
    modules: list[CharacterModuleResponse]
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run python -c "
from adapters.inbound.schemas import (
    ModuleDefinitionCreate, ModuleDefinitionUpdate, ModuleDefinitionResponse,
    SheetTemplateCreate, SheetTemplateUpdate, SheetTemplateResponse,
    TemplateAddModule, TemplateReorderModules,
    CharacterCreate, CharacterUpdate, CharacterResponse,
    CharacterModuleCreate, CharacterModuleUpdate, CharacterModuleResponse,
)
print('All schemas imported successfully')
"
```

Expected: `All schemas imported successfully`

- [ ] **Step 3: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/inbound/schemas.py && git commit -m "feat: add API request/response schemas"
```

---

## Task 6: Module routes

**Files:**
- Create: `src/adapters/inbound/routers/__init__.py`
- Create: `src/adapters/inbound/routers/modules.py`

- [ ] **Step 1: Create the router**

```python
# src/adapters/inbound/routers/modules.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adapters.inbound.schemas import (
    ModuleDefinitionCreate,
    ModuleDefinitionResponse,
    ModuleDefinitionUpdate,
)
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.session import get_db
from domain.models.field_definition import FieldDefinition
from domain.models.module_definition import ModuleDefinition

router = APIRouter(prefix="/modules", tags=["modules"])


def _get_repo(db: Session = Depends(get_db)) -> SQLModuleDefinitionRepository:
    return SQLModuleDefinitionRepository(db)


def _to_response(mod: ModuleDefinition) -> ModuleDefinitionResponse:
    return ModuleDefinitionResponse(
        id=mod.id,
        name=mod.name,
        description=mod.description,
        category=mod.category,
        fields=[f.model_dump() for f in mod.fields],
    )


@router.get("", response_model=list[ModuleDefinitionResponse])
def list_modules(repo: SQLModuleDefinitionRepository = Depends(_get_repo)):
    return [_to_response(m) for m in repo.list_all()]


@router.post("", response_model=ModuleDefinitionResponse, status_code=201)
def create_module(
    body: ModuleDefinitionCreate,
    repo: SQLModuleDefinitionRepository = Depends(_get_repo),
):
    mod = ModuleDefinition(
        name=body.name,
        description=body.description,
        category=body.category,
        fields=[FieldDefinition(**f.model_dump()) for f in body.fields],
    )
    repo.save(mod)
    return _to_response(mod)


@router.get("/{module_id}", response_model=ModuleDefinitionResponse)
def get_module(
    module_id: str,
    repo: SQLModuleDefinitionRepository = Depends(_get_repo),
):
    mod = repo.get_by_id(module_id)
    if mod is None:
        raise HTTPException(404, "Module definition not found")
    return _to_response(mod)


@router.patch("/{module_id}", response_model=ModuleDefinitionResponse)
def update_module(
    module_id: str,
    body: ModuleDefinitionUpdate,
    repo: SQLModuleDefinitionRepository = Depends(_get_repo),
):
    mod = repo.get_by_id(module_id)
    if mod is None:
        raise HTTPException(404, "Module definition not found")
    updated = ModuleDefinition(
        name=body.name if body.name is not None else mod.name,
        description=body.description if body.description is not None else mod.description,
        category=mod.category,
        fields=[FieldDefinition(**f.model_dump()) for f in body.fields] if body.fields is not None else mod.fields,
    )
    updated.__pydantic_private__["_id"] = mod.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.delete("/{module_id}", status_code=204)
def delete_module(
    module_id: str,
    repo: SQLModuleDefinitionRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    mod = repo.get_by_id(module_id)
    if mod is None:
        raise HTTPException(404, "Module definition not found")

    # Check if used by any template
    from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
    template_repo = SQLSheetTemplateRepository(db)
    for t in template_repo.list_all():
        if module_id in t.modules:
            raise HTTPException(409, "Module is used by a template")

    # Check if used by any character
    from adapters.outbound.db.character_repo import SQLCharacterRepository
    char_repo = SQLCharacterRepository(db)
    for c in char_repo.list_all():
        if any(m.definition_id == module_id for m in c.modules):
            raise HTTPException(409, "Module is used by a character")

    repo.delete(module_id)
```

- [ ] **Step 2: Create the routers package marker**

Create an empty `src/adapters/inbound/routers/__init__.py`.

- [ ] **Step 3: Verify import**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run python -c "
from adapters.inbound.routers.modules import router
print(f'Module router loaded with {len(router.routes)} routes')
"
```

Expected: `Module router loaded with 5 routes`

- [ ] **Step 4: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/inbound/routers/ && git commit -m "feat: add /modules API routes"
```

---

## Task 7: Template routes

**Files:**
- Create: `src/adapters/inbound/routers/templates.py`

- [ ] **Step 1: Create the router**

```python
# src/adapters/inbound/routers/templates.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adapters.inbound.schemas import (
    SheetTemplateCreate,
    SheetTemplateResponse,
    SheetTemplateUpdate,
    TemplateAddModule,
    TemplateReorderModules,
)
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
from adapters.outbound.db.character_repo import SQLCharacterRepository
from adapters.outbound.db.session import get_db
from domain.models.sheet_template import SheetTemplate

router = APIRouter(prefix="/templates", tags=["templates"])


def _get_repo(db: Session = Depends(get_db)) -> SQLSheetTemplateRepository:
    return SQLSheetTemplateRepository(db)


def _to_response(t: SheetTemplate) -> SheetTemplateResponse:
    return SheetTemplateResponse(id=t.id, name=t.name, system=t.system, modules=t.modules)


@router.get("", response_model=list[SheetTemplateResponse])
def list_templates(repo: SQLSheetTemplateRepository = Depends(_get_repo)):
    return [_to_response(t) for t in repo.list_all()]


@router.post("", response_model=SheetTemplateResponse, status_code=201)
def create_template(
    body: SheetTemplateCreate,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
):
    template = SheetTemplate(name=body.name, system=body.system)
    repo.save(template)
    return _to_response(template)


@router.get("/{template_id}", response_model=SheetTemplateResponse)
def get_template(template_id: str, repo: SQLSheetTemplateRepository = Depends(_get_repo)):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    return _to_response(t)


@router.patch("/{template_id}", response_model=SheetTemplateResponse)
def update_template(
    template_id: str,
    body: SheetTemplateUpdate,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    updated = SheetTemplate(
        name=body.name if body.name is not None else t.name,
        system=body.system if body.system is not None else t.system,
        modules=t.modules,
    )
    updated.__pydantic_private__["_id"] = t.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: str,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")

    char_repo = SQLCharacterRepository(db)
    for c in char_repo.list_all():
        if c.template_id == template_id:
            raise HTTPException(409, "Template is referenced by a character")

    repo.delete(template_id)


@router.post("/{template_id}/modules", response_model=SheetTemplateResponse)
def add_module_to_template(
    template_id: str,
    body: TemplateAddModule,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")

    mod_repo = SQLModuleDefinitionRepository(db)
    mod_def = mod_repo.get_by_id(body.definition_id)
    if mod_def is None:
        raise HTTPException(404, "Module definition not found")

    # One module per category
    existing_cats = {
        mod_repo.get_by_id(def_id).category
        for def_id in t.modules
        if mod_repo.get_by_id(def_id) is not None
    }
    if mod_def.category in existing_cats:
        raise HTTPException(409, f"Template already has a module in category '{mod_def.category}'")

    updated = SheetTemplate(
        name=t.name,
        system=t.system,
        modules=t.modules + [body.definition_id],
    )
    updated.__pydantic_private__["_id"] = t.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.delete("/{template_id}/modules/{definition_id}", response_model=SheetTemplateResponse)
def remove_module_from_template(
    template_id: str,
    definition_id: str,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    if definition_id not in t.modules:
        raise HTTPException(404, "Module not in template")

    updated = SheetTemplate(
        name=t.name,
        system=t.system,
        modules=[m for m in t.modules if m != definition_id],
    )
    updated.__pydantic_private__["_id"] = t.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.patch("/{template_id}/modules/order", response_model=SheetTemplateResponse)
def reorder_template_modules(
    template_id: str,
    body: TemplateReorderModules,
    repo: SQLSheetTemplateRepository = Depends(_get_repo),
):
    t = repo.get_by_id(template_id)
    if t is None:
        raise HTTPException(404, "Template not found")
    if set(body.module_ids) != set(t.modules):
        raise HTTPException(422, "module_ids must contain exactly the same IDs as the template's modules")

    updated = SheetTemplate(name=t.name, system=t.system, modules=body.module_ids)
    updated.__pydantic_private__["_id"] = t.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run python -c "
from adapters.inbound.routers.templates import router
print(f'Template router loaded with {len(router.routes)} routes')
"
```

Expected: `Template router loaded with 7 routes`

- [ ] **Step 3: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/inbound/routers/templates.py && git commit -m "feat: add /templates API routes with module management"
```

---

## Task 8: Character and character-module routes

**Files:**
- Create: `src/adapters/inbound/routers/characters.py`

- [ ] **Step 1: Create the router**

```python
# src/adapters/inbound/routers/characters.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from adapters.inbound.schemas import (
    CharacterCreate,
    CharacterModuleCreate,
    CharacterModuleResponse,
    CharacterModuleUpdate,
    CharacterResponse,
    CharacterUpdate,
)
from adapters.outbound.db.character_repo import SQLCharacterRepository
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
from adapters.outbound.db.session import get_db
from domain.models.character import Character
from domain.models.character_module import CharacterModule
from domain.models.field_definition import FieldType

router = APIRouter(prefix="/characters", tags=["characters"])


def _get_repo(db: Session = Depends(get_db)) -> SQLCharacterRepository:
    return SQLCharacterRepository(db)


def _to_response(char: Character) -> CharacterResponse:
    return CharacterResponse(
        id=char.id,
        player=char.player,
        name=char.name,
        template_id=char.template_id,
        modules=[
            CharacterModuleResponse(id=m.id, definition_id=m.definition_id, values=m.values)
            for m in char.modules
        ],
    )


def _default_values_for_module(mod_def) -> dict:
    return {
        f.name: f.default
        if f.default is not None
        else ([] if f.field_type == FieldType.LIST else 0 if f.field_type in (FieldType.INTEGER, FieldType.FLOAT) else False if f.field_type == FieldType.BOOLEAN else "")
        for f in mod_def.fields
    }


# ── Characters ───────────────────────────────────────────────────────────────

@router.get("", response_model=list[CharacterResponse])
def list_characters(
    player: str | None = Query(default=None),
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    if player:
        return [_to_response(c) for c in repo.list_by_player(player)]
    return [_to_response(c) for c in repo.list_all()]


@router.post("", response_model=CharacterResponse, status_code=201)
def create_character(
    body: CharacterCreate,
    repo: SQLCharacterRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    modules: list[CharacterModule] = []

    if body.template_id:
        tmpl_repo = SQLSheetTemplateRepository(db)
        mod_repo = SQLModuleDefinitionRepository(db)
        tmpl = tmpl_repo.get_by_id(body.template_id)
        if tmpl is None:
            raise HTTPException(404, "Template not found")
        for def_id in tmpl.modules:
            mod_def = mod_repo.get_by_id(def_id)
            if mod_def:
                modules.append(
                    CharacterModule(
                        definition_id=def_id,
                        values=_default_values_for_module(mod_def),
                    )
                )

    char = Character(
        player=body.player,
        name=body.name,
        template_id=body.template_id,
        modules=modules,
    )
    repo.save(char)
    return _to_response(char)


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(character_id: str, repo: SQLCharacterRepository = Depends(_get_repo)):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    return _to_response(char)


@router.patch("/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: str,
    body: CharacterUpdate,
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    updated = Character(
        player=body.player if body.player is not None else char.player,
        name=body.name if body.name is not None else char.name,
        template_id=char.template_id,
        modules=char.modules,
    )
    updated.__pydantic_private__["_id"] = char.__pydantic_private__["_id"]
    repo.save(updated)
    return _to_response(updated)


@router.delete("/{character_id}", status_code=204)
def delete_character(character_id: str, repo: SQLCharacterRepository = Depends(_get_repo)):
    if not repo.delete(character_id):
        raise HTTPException(404, "Character not found")


# ── Character modules ─────────────────────────────────────────────────────────

@router.get("/{character_id}/modules", response_model=list[CharacterModuleResponse])
def list_character_modules(
    character_id: str, repo: SQLCharacterRepository = Depends(_get_repo)
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    return [CharacterModuleResponse(id=m.id, definition_id=m.definition_id, values=m.values) for m in char.modules]


@router.post("/{character_id}/modules", response_model=CharacterModuleResponse, status_code=201)
def add_module_to_character(
    character_id: str,
    body: CharacterModuleCreate,
    repo: SQLCharacterRepository = Depends(_get_repo),
    db: Session = Depends(get_db),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")

    mod_repo = SQLModuleDefinitionRepository(db)
    mod_def = mod_repo.get_by_id(body.definition_id)
    if mod_def is None:
        raise HTTPException(404, "Module definition not found")

    # Enforce one module per category
    existing_cats = {
        mod_repo.get_by_id(m.definition_id).category
        for m in char.modules
        if mod_repo.get_by_id(m.definition_id) is not None
    }
    if mod_def.category in existing_cats:
        raise HTTPException(
            409, f"Character already has a module in category '{mod_def.category}'"
        )

    new_mod = CharacterModule(definition_id=body.definition_id, values=body.values)
    updated = Character(
        player=char.player,
        name=char.name,
        template_id=char.template_id,
        modules=char.modules + [new_mod],
    )
    updated.__pydantic_private__["_id"] = char.__pydantic_private__["_id"]
    repo.save(updated)
    return CharacterModuleResponse(id=new_mod.id, definition_id=new_mod.definition_id, values=new_mod.values)


@router.get("/{character_id}/modules/{module_id}", response_model=CharacterModuleResponse)
def get_character_module(
    character_id: str,
    module_id: str,
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    mod = next((m for m in char.modules if m.id == module_id), None)
    if mod is None:
        raise HTTPException(404, "Module not found on character")
    return CharacterModuleResponse(id=mod.id, definition_id=mod.definition_id, values=mod.values)


@router.patch("/{character_id}/modules/{module_id}", response_model=CharacterModuleResponse)
def update_character_module(
    character_id: str,
    module_id: str,
    body: CharacterModuleUpdate,
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    mod = next((m for m in char.modules if m.id == module_id), None)
    if mod is None:
        raise HTTPException(404, "Module not found on character")

    updated_mod = CharacterModule(definition_id=mod.definition_id, values=body.values)
    updated_mod.__pydantic_private__["_id"] = mod.__pydantic_private__["_id"]
    new_modules = [updated_mod if m.id == module_id else m for m in char.modules]
    updated_char = Character(
        player=char.player,
        name=char.name,
        template_id=char.template_id,
        modules=new_modules,
    )
    updated_char.__pydantic_private__["_id"] = char.__pydantic_private__["_id"]
    repo.save(updated_char)
    return CharacterModuleResponse(id=updated_mod.id, definition_id=updated_mod.definition_id, values=updated_mod.values)


@router.delete("/{character_id}/modules/{module_id}", status_code=204)
def remove_character_module(
    character_id: str,
    module_id: str,
    repo: SQLCharacterRepository = Depends(_get_repo),
):
    char = repo.get_by_id(character_id)
    if char is None:
        raise HTTPException(404, "Character not found")
    mod = next((m for m in char.modules if m.id == module_id), None)
    if mod is None:
        raise HTTPException(404, "Module not found on character")
    updated = Character(
        player=char.player,
        name=char.name,
        template_id=char.template_id,
        modules=[m for m in char.modules if m.id != module_id],
    )
    updated.__pydantic_private__["_id"] = char.__pydantic_private__["_id"]
    repo.save(updated)
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run python -c "
from adapters.inbound.routers.characters import router
print(f'Character router loaded with {len(router.routes)} routes')
"
```

Expected: `Character router loaded with 10 routes`

- [ ] **Step 3: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/inbound/routers/characters.py && git commit -m "feat: add /characters and character module API routes"
```

---

## Task 9: D&D 5e Seeder

**Files:**
- Create: `src/domain/seeder.py`

- [ ] **Step 1: Create the seeder**

```python
# src/domain/seeder.py
from domain.models.field_definition import FieldDefinition, FieldType
from domain.models.module_definition import ModuleDefinition
from domain.models.sheet_template import SheetTemplate
from domain.ports.outbound.module_definition_repository import ModuleDefinitionRepository
from domain.ports.outbound.sheet_template_repository import SheetTemplateRepository


def _int(name: str, default: int = 0) -> FieldDefinition:
    return FieldDefinition(name=name, field_type=FieldType.INTEGER, default=default)


def _str(name: str) -> FieldDefinition:
    return FieldDefinition(name=name, field_type=FieldType.STRING, default="")


def _lst(name: str) -> FieldDefinition:
    return FieldDefinition(name=name, field_type=FieldType.LIST, default=[])


DND5E_MODULES = [
    ModuleDefinition(
        name="D&D 5e Hit Points",
        category="health",
        description="Hit point tracking",
        fields=[_int("max_hp", 10), _int("current_hp", 10), _int("temp_hp")],
    ),
    ModuleDefinition(
        name="D&D 5e Experience",
        category="experience",
        description="XP and level tracking",
        fields=[_int("xp"), _int("level", 1)],
    ),
    ModuleDefinition(
        name="D&D 5e Ability Scores",
        category="attributes",
        description="The six core ability scores",
        fields=[
            _int("strength", 10),
            _int("dexterity", 10),
            _int("constitution", 10),
            _int("intelligence", 10),
            _int("wisdom", 10),
            _int("charisma", 10),
        ],
    ),
    ModuleDefinition(
        name="D&D 5e Combat Stats",
        category="combat",
        description="AC, initiative, speed, proficiency bonus",
        fields=[
            _int("armor_class", 10),
            _int("initiative"),
            _int("speed", 30),
            _int("proficiency_bonus", 2),
            _int("inspiration"),
        ],
    ),
    ModuleDefinition(
        name="D&D 5e Death Saves",
        category="death_saves",
        description="Death saving throw tracking",
        fields=[_int("successes"), _int("failures")],
    ),
    ModuleDefinition(
        name="D&D 5e Spell Slots",
        category="spells",
        description="Spell slot tracking by level",
        fields=[
            f
            for level in range(1, 10)
            for f in (_int(f"level_{level}_total"), _int(f"level_{level}_used"))
        ],
    ),
    ModuleDefinition(
        name="D&D 5e Currency",
        category="money",
        description="Coin purse",
        fields=[_int("cp"), _int("sp"), _int("ep"), _int("gp"), _int("pp")],
    ),
    ModuleDefinition(
        name="D&D 5e Proficiencies",
        category="proficiencies",
        description="Weapons, armor, tools, languages",
        fields=[_lst("weapons"), _lst("armor"), _lst("tools"), _lst("languages")],
    ),
    ModuleDefinition(
        name="D&D 5e Features",
        category="features",
        description="Class features, feats, racial traits",
        fields=[_lst("features")],
    ),
    ModuleDefinition(
        name="D&D 5e Background",
        category="background",
        description="Backstory and personality",
        fields=[
            _str("backstory"),
            _str("appearance"),
            _str("allies"),
            _str("personality_traits"),
            _str("ideals"),
            _str("bonds"),
            _str("flaws"),
        ],
    ),
    ModuleDefinition(
        name="D&D 5e Identity",
        category="identity",
        description="Race, class, alignment",
        fields=[_str("race"), _str("subrace"), _str("class"), _str("alignment")],
    ),
]

DND5E_TEMPLATE_NAME = "D&D 5e Base"


def seed_dnd5e(
    module_repo: ModuleDefinitionRepository,
    template_repo: SheetTemplateRepository,
) -> None:
    # Idempotent: skip if already seeded
    existing = {m.name for m in module_repo.list_all()}
    if DND5E_TEMPLATE_NAME in {t.name for t in template_repo.list_all()}:
        return

    seeded_modules: list[ModuleDefinition] = []
    for mod in DND5E_MODULES:
        if mod.name not in existing:
            module_repo.save(mod)
            seeded_modules.append(mod)
        else:
            # Find and use the existing one so template IDs are consistent
            all_mods = module_repo.list_all()
            seeded_modules.append(next(m for m in all_mods if m.name == mod.name))

    template = SheetTemplate(
        name=DND5E_TEMPLATE_NAME,
        system="D&D 5e",
        modules=[m.id for m in seeded_modules],
    )
    template_repo.save(template)
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run python -c "
from domain.seeder import seed_dnd5e, DND5E_MODULES, DND5E_TEMPLATE_NAME
print(f'Seeder loaded: {len(DND5E_MODULES)} modules, template name: {DND5E_TEMPLATE_NAME}')
"
```

Expected: `Seeder loaded: 11 modules, template name: D&D 5e Base`

- [ ] **Step 3: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/domain/seeder.py && git commit -m "feat: add D&D 5e seeder (11 modules + base template)"
```

---

## Task 10: Wire-up main.py + lifespan + cleanup

**Files:**
- Rewrite: `src/main.py`
- Delete: `src/adapters/outbound/db.py`, `src/adapters/inbound/api.py`, `src/adapters/inbound/user.py`

- [ ] **Step 1: Rewrite main.py**

```python
# src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI

from adapters.inbound.routers.modules import router as modules_router
from adapters.inbound.routers.templates import router as templates_router
from adapters.inbound.routers.characters import router as characters_router
from adapters.outbound.db.models import Base
from adapters.outbound.db.session import engine, SessionLocal
from adapters.outbound.db.module_definition_repo import SQLModuleDefinitionRepository
from adapters.outbound.db.sheet_template_repo import SQLSheetTemplateRepository
from domain.seeder import seed_dnd5e


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        seed_dnd5e(
            SQLModuleDefinitionRepository(session),
            SQLSheetTemplateRepository(session),
        )
    yield


app = FastAPI(title="Character Manager", lifespan=lifespan)

app.include_router(modules_router)
app.include_router(templates_router)
app.include_router(characters_router)
```

- [ ] **Step 2: Delete old placeholder files**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git rm src/adapters/outbound/db.py src/adapters/inbound/api.py src/adapters/inbound/user.py
```

- [ ] **Step 3: Update Dockerfile CMD to use uvicorn directly**

Change line 12 in the Dockerfile from:
```
CMD ["fastapi", "run", "src/main.py", "--port", "8000"]
```
to:
```
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

The working directory is `/app/src` — wait, actually the Dockerfile copies into `/app` and the PYTHONPATH isn't set. Let me update the Dockerfile to also set `PYTHONPATH`:

Full updated Dockerfile:
```dockerfile
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev
COPY src/ ./src/

FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Verify the app starts with a local SQLite database**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run python -c "
from main import app
print(f'App created: {app.title}')
print(f'Routes: {[r.path for r in app.routes]}')
"
```

Expected: App created with routes listing /modules, /templates, /characters paths.

- [ ] **Step 5: Verify the full test suite still passes**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/ -v
```

Expected: All unit tests pass (60+ tests).

- [ ] **Step 6: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/main.py Dockerfile && git commit -m "feat: wire up FastAPI app with lifespan, routers, and seeder"
```

---

## Task 11: Integration tests

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/conftest.py`
- Create: `tests/integration/test_golden_paths.py`

- [ ] **Step 1: Create the integration test conftest**

```python
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
    import os
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
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
```

- [ ] **Step 2: Create the golden path tests**

```python
# tests/integration/test_golden_paths.py
import pytest


def test_list_modules_returns_dnd5e_seed(client):
    response = client.get("/modules")
    assert response.status_code == 200
    modules = response.json()
    names = {m["name"] for m in modules}
    assert "D&D 5e Hit Points" in names
    assert "D&D 5e Ability Scores" in names
    assert len(modules) == 11


def test_get_dnd5e_template(client):
    response = client.get("/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 1
    assert templates[0]["name"] == "D&D 5e Base"
    assert templates[0]["system"] == "D&D 5e"
    assert len(templates[0]["modules"]) == 11


def test_create_character_without_template(client):
    response = client.post("/characters", json={"player": "player-1", "name": "Thorn"})
    assert response.status_code == 201
    char = response.json()
    assert char["name"] == "Thorn"
    assert char["player"] == "player-1"
    assert char["modules"] == []


def test_create_dnd5e_character_from_template(client):
    # Get the D&D 5e Base template
    templates_resp = client.get("/templates")
    template_id = templates_resp.json()[0]["id"]

    # Create character from template
    response = client.post(
        "/characters",
        json={"player": "player-1", "name": "Aragorn", "template_id": template_id},
    )
    assert response.status_code == 201
    char = response.json()
    assert char["name"] == "Aragorn"
    assert char["template_id"] == template_id
    assert len(char["modules"]) == 11


def test_get_character_with_modules(client):
    # Create a character
    templates_resp = client.get("/templates")
    template_id = templates_resp.json()[0]["id"]
    create_resp = client.post(
        "/characters",
        json={"player": "player-2", "name": "Gandalf", "template_id": template_id},
    )
    char_id = create_resp.json()["id"]

    # Retrieve it
    response = client.get(f"/characters/{char_id}")
    assert response.status_code == 200
    char = response.json()
    assert char["name"] == "Gandalf"
    assert len(char["modules"]) == 11

    # Health module should have default values
    modules_resp = client.get(f"/characters/{char_id}/modules")
    modules = modules_resp.json()
    health_mod = next(
        m for m in modules
        if any(k in m["values"] for k in ("max_hp", "current_hp"))
    )
    assert health_mod["values"]["max_hp"] == 10
    assert health_mod["values"]["current_hp"] == 10


def test_update_character_hp(client):
    # Create character
    templates_resp = client.get("/templates")
    template_id = templates_resp.json()[0]["id"]
    create_resp = client.post(
        "/characters",
        json={"player": "player-3", "name": "Legolas", "template_id": template_id},
    )
    char = create_resp.json()
    char_id = char["id"]

    # Find the health module
    modules_resp = client.get(f"/characters/{char_id}/modules")
    modules = modules_resp.json()
    health_mod = next(m for m in modules if "max_hp" in m["values"])
    mod_id = health_mod["id"]

    # Update HP
    update_resp = client.patch(
        f"/characters/{char_id}/modules/{mod_id}",
        json={"values": {"max_hp": 45, "current_hp": 38, "temp_hp": 5}},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["values"]["max_hp"] == 45
    assert updated["values"]["current_hp"] == 38
    assert updated["values"]["temp_hp"] == 5

    # Verify persistence
    verify_resp = client.get(f"/characters/{char_id}/modules/{mod_id}")
    assert verify_resp.json()["values"]["current_hp"] == 38


def test_add_custom_module_to_character(client):
    # Create a custom module definition
    create_mod_resp = client.post(
        "/modules",
        json={
            "name": "Custom Sanity",
            "category": "sanity",
            "fields": [
                {"name": "max_sanity", "field_type": "integer", "default": 100},
                {"name": "current_sanity", "field_type": "integer", "default": 100},
            ],
        },
    )
    assert create_mod_resp.status_code == 201
    custom_mod_id = create_mod_resp.json()["id"]

    # Create a character without template
    char_resp = client.post(
        "/characters", json={"player": "player-4", "name": "Investigator"}
    )
    char_id = char_resp.json()["id"]

    # Add custom module to character
    add_resp = client.post(
        f"/characters/{char_id}/modules",
        json={"definition_id": custom_mod_id, "values": {"max_sanity": 80, "current_sanity": 75}},
    )
    assert add_resp.status_code == 201
    added = add_resp.json()
    assert added["values"]["max_sanity"] == 80


def test_category_uniqueness_constraint(client):
    # Create character with health module
    templates_resp = client.get("/templates")
    template_id = templates_resp.json()[0]["id"]
    char_resp = client.post(
        "/characters",
        json={"player": "player-5", "name": "Fighter", "template_id": template_id},
    )
    char_id = char_resp.json()["id"]

    # Get any health module definition
    modules_resp = client.get("/modules")
    health_mod = next(m for m in modules_resp.json() if m["category"] == "health")

    # Try to add a second health module — should fail with 409
    add_resp = client.post(
        f"/characters/{char_id}/modules",
        json={"definition_id": health_mod["id"], "values": {}},
    )
    assert add_resp.status_code == 409
    assert "category" in add_resp.json()["detail"].lower()


def test_update_character_name(client):
    create_resp = client.post(
        "/characters", json={"player": "player-6", "name": "Old Name"}
    )
    char_id = create_resp.json()["id"]

    update_resp = client.patch(f"/characters/{char_id}", json={"name": "New Name"})
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "New Name"


def test_delete_character(client):
    create_resp = client.post(
        "/characters", json={"player": "player-7", "name": "Temp"}
    )
    char_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/characters/{char_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/characters/{char_id}")
    assert get_resp.status_code == 404


def test_list_characters_filtered_by_player(client):
    client.post("/characters", json={"player": "filter-player", "name": "A"})
    client.post("/characters", json={"player": "filter-player", "name": "B"})
    client.post("/characters", json={"player": "other-player", "name": "C"})

    response = client.get("/characters?player=filter-player")
    assert response.status_code == 200
    chars = response.json()
    assert len(chars) == 2
    assert all(c["player"] == "filter-player" for c in chars)
```

- [ ] **Step 3: Run integration tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/integration/ -v
```

Expected: All tests pass (9 tests). If any fail, investigate and fix before committing.

- [ ] **Step 4: Run the full test suite**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest -v
```

Expected: All tests pass (70+ tests).

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add tests/integration/ && git commit -m "test: add integration tests for D&D 5e character sheet golden paths"
```

---

## Task 12: Docker smoke test and final push

- [ ] **Step 1: Build and start the stack**

```bash
cd /Users/marthox/Dev/character-vault && docker compose up --build -d
```

Wait ~10 seconds for startup, then:

- [ ] **Step 2: Smoke test the running service**

```bash
curl -s http://localhost:8000/modules | python3 -m json.tool | head -30
```

Expected: JSON array with D&D 5e module definitions.

```bash
curl -s http://localhost:8000/templates | python3 -m json.tool
```

Expected: JSON array with "D&D 5e Base" template.

```bash
# Create a D&D 5e character
TEMPLATE_ID=$(curl -s http://localhost:8000/templates | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
curl -s -X POST http://localhost:8000/characters \
  -H "Content-Type: application/json" \
  -d "{\"player\": \"player-uuid-1\", \"name\": \"Aria Stormwind\", \"template_id\": \"$TEMPLATE_ID\"}" \
  | python3 -m json.tool
```

Expected: Character created with 11 modules and their default values.

```bash
# Update HP
CHAR_ID=$(curl -s http://localhost:8000/characters | python3 -c "import sys,json; chars=json.load(sys.stdin); print(chars[-1]['id'])")
HP_MOD_ID=$(curl -s http://localhost:8000/characters/$CHAR_ID/modules | python3 -c "import sys,json; mods=json.load(sys.stdin); print(next(m['id'] for m in mods if 'max_hp' in m['values']))")
curl -s -X PATCH http://localhost:8000/characters/$CHAR_ID/modules/$HP_MOD_ID \
  -H "Content-Type: application/json" \
  -d '{"values": {"max_hp": 52, "current_hp": 47, "temp_hp": 0}}' \
  | python3 -m json.tool
```

Expected: Updated HP values returned.

- [ ] **Step 3: Tear down**

```bash
cd /Users/marthox/Dev/character-vault && docker compose down
```

- [ ] **Step 4: Push character-manager and update submodule pointer**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git push
```

```bash
cd /Users/marthox/Dev/character-vault && git add services/character-manager && git commit -m "Update character-manager: Plan B — full API, DB, D&D 5e seeding"
```

```bash
cd /Users/marthox/Dev/character-vault && git push
```
