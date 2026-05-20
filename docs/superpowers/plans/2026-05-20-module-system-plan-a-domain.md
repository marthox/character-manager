# Character Sheet Module System — Plan A: Domain Layer

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat `Character` model with the composable module system domain layer: five new models, three repository ports, three in-memory repository adapters, and a cleaned-up test suite.

**Architecture:** Hexagonal architecture (existing pattern). All new models extend `BaseClass` (for UUID identity) or `BaseModel` (for embedded value objects). Repository ports are abstract base classes. In-memory adapters are the only concrete implementations in this plan — no HTTP, no DB, no seeding. Plan B handles the API, seeding, and wire-up.

**Tech Stack:** Python 3.13, Pydantic v2, pytest, uv

---

## File Map

### Create
| File | Purpose |
|------|---------|
| `src/domain/models/field_definition.py` | `FieldType` enum + `FieldDefinition` value object |
| `src/domain/models/module_definition.py` | `ModuleDefinition` entity with category validation |
| `src/domain/models/sheet_template.py` | `SheetTemplate` entity |
| `src/domain/models/character_module.py` | `CharacterModule` entity |
| `src/domain/ports/outbound/module_definition_repository.py` | Abstract repository for `ModuleDefinition` |
| `src/domain/ports/outbound/sheet_template_repository.py` | Abstract repository for `SheetTemplate` |
| `src/adapters/outbound/memory/__init__.py` | Package marker |
| `src/adapters/outbound/memory/module_definition_repo.py` | In-memory `ModuleDefinition` repository |
| `src/adapters/outbound/memory/sheet_template_repo.py` | In-memory `SheetTemplate` repository |
| `src/adapters/outbound/memory/character_repo.py` | In-memory `Character` repository |
| `tests/unit/models/test_field_definition.py` | Unit tests for `FieldDefinition` |
| `tests/unit/models/test_module_definition.py` | Unit tests for `ModuleDefinition` |
| `tests/unit/models/test_sheet_template.py` | Unit tests for `SheetTemplate` |
| `tests/unit/models/test_character_module.py` | Unit tests for `CharacterModule` |
| `tests/unit/models/test_character_rewrite.py` | Unit tests for new `Character` |
| `tests/unit/repositories/test_module_definition_repo.py` | Tests for in-memory `ModuleDefinitionRepo` |
| `tests/unit/repositories/test_sheet_template_repo.py` | Tests for in-memory `SheetTemplateRepo` |
| `tests/unit/repositories/test_character_repo.py` | Tests for in-memory `CharacterRepo` |

### Rewrite
| File | Change |
|------|--------|
| `src/domain/models/character.py` | Replace flat D&D model with composable `Character` |
| `src/domain/ports/outbound/character_repository.py` | Update to new `Character` signature |
| `tests/conftest.py` | Replace with minimal fixture for new model |

### Delete (after all tests pass)
```
src/domain/models/alignment.py
src/domain/models/attack.py
src/domain/models/attribute.py
src/domain/models/background.py
src/domain/models/character_class.py
src/domain/models/death_saves.py
src/domain/models/feature.py
src/domain/models/item.py
src/domain/models/money.py
src/domain/models/race.py
src/domain/models/skill.py
src/domain/models/spell.py
src/domain/models/spell_components.py
src/domain/models/spell_slots.py
src/domain/models/subrace.py
src/domain/utils/character_utils.py
tests/factories/character_factory.py
tests/unit/models/test_character.py
tests/unit/models/test_utils.py
```

---

## Task 1: FieldDefinition

**Files:**
- Create: `src/domain/models/field_definition.py`
- Test: `tests/unit/models/test_field_definition.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/models/test_field_definition.py
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_field_definition.py -v
```

Expected: `ModuleNotFoundError: No module named 'domain.models.field_definition'`

- [ ] **Step 3: Create the implementation**

```python
# src/domain/models/field_definition.py
from typing import Any
from enum import Enum
from pydantic import BaseModel


class FieldType(str, Enum):
    INTEGER = "integer"
    STRING = "string"
    BOOLEAN = "boolean"
    FLOAT = "float"
    LIST = "list"


class FieldDefinition(BaseModel):
    name: str
    field_type: FieldType
    required: bool = True
    default: Any = None
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_field_definition.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/domain/models/field_definition.py tests/unit/models/test_field_definition.py && git commit -m "feat: add FieldType enum and FieldDefinition model"
```

---

## Task 2: ModuleDefinition

**Files:**
- Create: `src/domain/models/module_definition.py`
- Test: `tests/unit/models/test_module_definition.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/models/test_module_definition.py
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_module_definition.py -v
```

Expected: `ModuleNotFoundError: No module named 'domain.models.module_definition'`

- [ ] **Step 3: Create the implementation**

```python
# src/domain/models/module_definition.py
import re
from pydantic import field_validator
from domain.models.base_class import BaseClass
from domain.models.field_definition import FieldDefinition


class ModuleDefinition(BaseClass):
    name: str
    description: str | None = None
    category: str
    fields: list[FieldDefinition] = []

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        normalized = v.lower().strip()
        if not re.match(r"^[a-z][a-z0-9_]*$", normalized):
            raise ValueError(
                f"Category '{normalized}' is invalid. "
                "Must start with a letter and contain only lowercase letters, digits, or underscores."
            )
        return normalized
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_module_definition.py -v
```

Expected: `13 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/domain/models/module_definition.py tests/unit/models/test_module_definition.py && git commit -m "feat: add ModuleDefinition model with category validation"
```

---

## Task 3: SheetTemplate

**Files:**
- Create: `src/domain/models/sheet_template.py`
- Test: `tests/unit/models/test_sheet_template.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/models/test_sheet_template.py
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_sheet_template.py -v
```

Expected: `ModuleNotFoundError: No module named 'domain.models.sheet_template'`

- [ ] **Step 3: Create the implementation**

```python
# src/domain/models/sheet_template.py
from domain.models.base_class import BaseClass


class SheetTemplate(BaseClass):
    name: str
    system: str
    modules: list[str] = []
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_sheet_template.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/domain/models/sheet_template.py tests/unit/models/test_sheet_template.py && git commit -m "feat: add SheetTemplate model"
```

---

## Task 4: CharacterModule

**Files:**
- Create: `src/domain/models/character_module.py`
- Test: `tests/unit/models/test_character_module.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/models/test_character_module.py
import pytest
from domain.models.character_module import CharacterModule


def test_character_module_has_uuid():
    mod = CharacterModule(definition_id="some-def-id", values={})
    assert len(mod.id) == 36
    assert mod.id.count("-") == 4


def test_two_character_modules_have_different_ids():
    a = CharacterModule(definition_id="id-1")
    b = CharacterModule(definition_id="id-2")
    assert a.id != b.id


def test_character_module_stores_values():
    mod = CharacterModule(
        definition_id="health-def-id",
        values={"max_hp": 45, "current_hp": 30, "temp_hp": 0},
    )
    assert mod.values["max_hp"] == 45
    assert mod.values["current_hp"] == 30
    assert mod.values["temp_hp"] == 0


def test_character_module_default_empty_values():
    mod = CharacterModule(definition_id="some-id")
    assert mod.values == {}


def test_character_module_stores_string_values():
    mod = CharacterModule(
        definition_id="identity-def-id",
        values={"race": "Elf", "class": "Wizard", "alignment": "Neutral Good"},
    )
    assert mod.values["race"] == "Elf"


def test_character_module_stores_list_values():
    mod = CharacterModule(
        definition_id="proficiencies-def-id",
        values={"languages": ["Common", "Elvish", "Dwarvish"]},
    )
    assert mod.values["languages"] == ["Common", "Elvish", "Dwarvish"]
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_character_module.py -v
```

Expected: `ModuleNotFoundError: No module named 'domain.models.character_module'`

- [ ] **Step 3: Create the implementation**

```python
# src/domain/models/character_module.py
from typing import Any
from domain.models.base_class import BaseClass


class CharacterModule(BaseClass):
    definition_id: str
    values: dict[str, Any] = {}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_character_module.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/domain/models/character_module.py tests/unit/models/test_character_module.py && git commit -m "feat: add CharacterModule model"
```

---

## Task 5: Character (rewrite)

**Files:**
- Modify: `src/domain/models/character.py`
- Create: `tests/unit/models/test_character_rewrite.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/models/test_character_rewrite.py
import pytest
from domain.models.character import Character
from domain.models.character_module import CharacterModule


def test_character_creation_minimal():
    char = Character(player="player-uuid")
    assert char.player == "player-uuid"
    assert char.name is None
    assert char.template_id is None
    assert char.modules == []


def test_character_has_uuid():
    char = Character(player="player-uuid")
    assert len(char.id) == 36


def test_two_characters_have_different_ids():
    a = Character(player="player-uuid")
    b = Character(player="player-uuid")
    assert a.id != b.id


def test_character_with_name():
    char = Character(player="player-uuid", name="Aragorn")
    assert char.name == "Aragorn"


def test_character_with_template():
    char = Character(player="player-uuid", template_id="dnd5e-template-id")
    assert char.template_id == "dnd5e-template-id"


def test_character_with_modules():
    hp_module = CharacterModule(
        definition_id="health-def-id",
        values={"max_hp": 45, "current_hp": 45, "temp_hp": 0},
    )
    char = Character(player="player-uuid", name="Legolas", modules=[hp_module])
    assert len(char.modules) == 1
    assert char.modules[0].values["max_hp"] == 45


def test_character_modules_preserve_order():
    mod_a = CharacterModule(definition_id="health-id", values={})
    mod_b = CharacterModule(definition_id="experience-id", values={})
    mod_c = CharacterModule(definition_id="attributes-id", values={})
    char = Character(player="player-uuid", modules=[mod_a, mod_b, mod_c])
    assert char.modules[0].definition_id == "health-id"
    assert char.modules[1].definition_id == "experience-id"
    assert char.modules[2].definition_id == "attributes-id"
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_character_rewrite.py -v
```

Expected: `ImportError` or `TypeError` — old `Character` model has incompatible fields.

- [ ] **Step 3: Rewrite `character.py`**

```python
# src/domain/models/character.py
from domain.models.base_class import BaseClass
from domain.models.character_module import CharacterModule


class Character(BaseClass):
    player: str
    name: str | None = None
    template_id: str | None = None
    modules: list[CharacterModule] = []
```

- [ ] **Step 4: Run new tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/models/test_character_rewrite.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/domain/models/character.py tests/unit/models/test_character_rewrite.py && git commit -m "feat: rewrite Character as composable module container"
```

---

## Task 6: Repository ports

Ports are abstract base classes — no tests at this level. The in-memory implementations (Tasks 7–9) are the test subjects.

**Files:**
- Create: `src/domain/ports/outbound/module_definition_repository.py`
- Create: `src/domain/ports/outbound/sheet_template_repository.py`
- Modify: `src/domain/ports/outbound/character_repository.py`

- [ ] **Step 1: Create ModuleDefinition repository port**

```python
# src/domain/ports/outbound/module_definition_repository.py
from abc import ABC, abstractmethod
from domain.models.module_definition import ModuleDefinition


class ModuleDefinitionRepository(ABC):
    @abstractmethod
    def save(self, module: ModuleDefinition) -> ModuleDefinition:
        """Persist a module definition and return it."""

    @abstractmethod
    def get_by_id(self, module_id: str) -> ModuleDefinition | None:
        """Return a module definition by id, or None if not found."""

    @abstractmethod
    def list_all(self) -> list[ModuleDefinition]:
        """Return all module definitions."""

    @abstractmethod
    def delete(self, module_id: str) -> bool:
        """Delete a module definition. Returns True if deleted, False if not found."""
```

- [ ] **Step 2: Create SheetTemplate repository port**

```python
# src/domain/ports/outbound/sheet_template_repository.py
from abc import ABC, abstractmethod
from domain.models.sheet_template import SheetTemplate


class SheetTemplateRepository(ABC):
    @abstractmethod
    def save(self, template: SheetTemplate) -> SheetTemplate:
        """Persist a sheet template and return it."""

    @abstractmethod
    def get_by_id(self, template_id: str) -> SheetTemplate | None:
        """Return a sheet template by id, or None if not found."""

    @abstractmethod
    def list_all(self) -> list[SheetTemplate]:
        """Return all sheet templates."""

    @abstractmethod
    def delete(self, template_id: str) -> bool:
        """Delete a sheet template. Returns True if deleted, False if not found."""
```

- [ ] **Step 3: Rewrite Character repository port**

```python
# src/domain/ports/outbound/character_repository.py
from abc import ABC, abstractmethod
from domain.models.character import Character


class CharacterRepository(ABC):
    @abstractmethod
    def save(self, character: Character) -> Character:
        """Persist a character and return it."""

    @abstractmethod
    def get_by_id(self, character_id: str) -> Character | None:
        """Return a character by id, or None if not found."""

    @abstractmethod
    def list_by_player(self, player_id: str) -> list[Character]:
        """Return all characters belonging to a player."""

    @abstractmethod
    def list_all(self) -> list[Character]:
        """Return all characters."""

    @abstractmethod
    def delete(self, character_id: str) -> bool:
        """Delete a character. Returns True if deleted, False if not found."""
```

- [ ] **Step 4: Verify no import errors**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run python -c "
from domain.ports.outbound.module_definition_repository import ModuleDefinitionRepository
from domain.ports.outbound.sheet_template_repository import SheetTemplateRepository
from domain.ports.outbound.character_repository import CharacterRepository
print('All ports imported successfully')
"
```

Expected: `All ports imported successfully`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/domain/ports/outbound/ && git commit -m "feat: add repository ports for ModuleDefinition, SheetTemplate, Character"
```

---

## Task 7: In-memory ModuleDefinition repository

**Files:**
- Create: `src/adapters/outbound/memory/__init__.py`
- Create: `src/adapters/outbound/memory/module_definition_repo.py`
- Create: `tests/unit/repositories/__init__.py`
- Test: `tests/unit/repositories/test_module_definition_repo.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/repositories/test_module_definition_repo.py
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_module_definition_repo.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.outbound.memory'`

- [ ] **Step 3: Create the package and implementation**

```python
# src/adapters/outbound/memory/__init__.py
```

```python
# src/adapters/outbound/memory/module_definition_repo.py
from domain.models.module_definition import ModuleDefinition
from domain.ports.outbound.module_definition_repository import ModuleDefinitionRepository


class InMemoryModuleDefinitionRepository(ModuleDefinitionRepository):
    def __init__(self):
        self._store: dict[str, ModuleDefinition] = {}

    def save(self, module: ModuleDefinition) -> ModuleDefinition:
        self._store[module.id] = module
        return module

    def get_by_id(self, module_id: str) -> ModuleDefinition | None:
        return self._store.get(module_id)

    def list_all(self) -> list[ModuleDefinition]:
        return list(self._store.values())

    def delete(self, module_id: str) -> bool:
        if module_id not in self._store:
            return False
        del self._store[module_id]
        return True
```

Also create the test package marker:

```python
# tests/unit/repositories/__init__.py
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_module_definition_repo.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/outbound/memory/ tests/unit/repositories/ && git commit -m "feat: add in-memory ModuleDefinition repository"
```

---

## Task 8: In-memory SheetTemplate repository

**Files:**
- Create: `src/adapters/outbound/memory/sheet_template_repo.py`
- Test: `tests/unit/repositories/test_sheet_template_repo.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/repositories/test_sheet_template_repo.py
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
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_sheet_template_repo.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.outbound.memory.sheet_template_repo'`

- [ ] **Step 3: Create the implementation**

```python
# src/adapters/outbound/memory/sheet_template_repo.py
from domain.models.sheet_template import SheetTemplate
from domain.ports.outbound.sheet_template_repository import SheetTemplateRepository


class InMemorySheetTemplateRepository(SheetTemplateRepository):
    def __init__(self):
        self._store: dict[str, SheetTemplate] = {}

    def save(self, template: SheetTemplate) -> SheetTemplate:
        self._store[template.id] = template
        return template

    def get_by_id(self, template_id: str) -> SheetTemplate | None:
        return self._store.get(template_id)

    def list_all(self) -> list[SheetTemplate]:
        return list(self._store.values())

    def delete(self, template_id: str) -> bool:
        if template_id not in self._store:
            return False
        del self._store[template_id]
        return True
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_sheet_template_repo.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/outbound/memory/sheet_template_repo.py tests/unit/repositories/test_sheet_template_repo.py && git commit -m "feat: add in-memory SheetTemplate repository"
```

---

## Task 9: In-memory Character repository

**Files:**
- Create: `src/adapters/outbound/memory/character_repo.py`
- Test: `tests/unit/repositories/test_character_repo.py`

- [ ] **Step 1: Create the test file**

```python
# tests/unit/repositories/test_character_repo.py
import pytest
from domain.models.character import Character
from domain.models.character_module import CharacterModule
from adapters.outbound.memory.character_repo import InMemoryCharacterRepository


@pytest.fixture
def repo():
    return InMemoryCharacterRepository()


@pytest.fixture
def aragorn():
    return Character(
        player="player-1",
        name="Aragorn",
        modules=[
            CharacterModule(definition_id="health-id", values={"max_hp": 90, "current_hp": 90, "temp_hp": 0})
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
    assert retrieved.name == "Aragorn"
    assert retrieved.modules[0].values["max_hp"] == 90


def test_get_by_id_returns_none_when_not_found(repo):
    assert repo.get_by_id("nonexistent-id") is None


def test_list_all_empty(repo):
    assert repo.list_all() == []


def test_list_all_returns_all_saved(repo, aragorn, gandalf):
    repo.save(aragorn)
    repo.save(gandalf)
    assert len(repo.list_all()) == 2


def test_list_by_player_returns_only_that_players_characters(repo, aragorn, legolas, gandalf):
    repo.save(aragorn)
    repo.save(legolas)
    repo.save(gandalf)
    player1_chars = repo.list_by_player("player-1")
    assert len(player1_chars) == 2
    names = {c.name for c in player1_chars}
    assert names == {"Aragorn", "Legolas"}


def test_list_by_player_returns_empty_for_unknown_player(repo, aragorn):
    repo.save(aragorn)
    assert repo.list_by_player("unknown-player") == []


def test_delete_existing(repo, aragorn):
    repo.save(aragorn)
    result = repo.delete(aragorn.id)
    assert result is True
    assert repo.get_by_id(aragorn.id) is None


def test_delete_nonexistent_returns_false(repo):
    assert repo.delete("nonexistent-id") is False


def test_each_repo_instance_is_independent():
    repo_a = InMemoryCharacterRepository()
    repo_b = InMemoryCharacterRepository()
    char = Character(player="player-1", name="Frodo")
    repo_a.save(char)
    assert repo_b.get_by_id(char.id) is None
```

- [ ] **Step 2: Run test to confirm it fails**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_character_repo.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.outbound.memory.character_repo'`

- [ ] **Step 3: Create the implementation**

```python
# src/adapters/outbound/memory/character_repo.py
from domain.models.character import Character
from domain.ports.outbound.character_repository import CharacterRepository


class InMemoryCharacterRepository(CharacterRepository):
    def __init__(self):
        self._store: dict[str, Character] = {}

    def save(self, character: Character) -> Character:
        self._store[character.id] = character
        return character

    def get_by_id(self, character_id: str) -> Character | None:
        return self._store.get(character_id)

    def list_by_player(self, player_id: str) -> list[Character]:
        return [c for c in self._store.values() if c.player == player_id]

    def list_all(self) -> list[Character]:
        return list(self._store.values())

    def delete(self, character_id: str) -> bool:
        if character_id not in self._store:
            return False
        del self._store[character_id]
        return True
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest tests/unit/repositories/test_character_repo.py -v
```

Expected: `9 passed`

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add src/adapters/outbound/memory/character_repo.py tests/unit/repositories/test_character_repo.py && git commit -m "feat: add in-memory Character repository"
```

---

## Task 10: Cleanup — remove old models and update conftest

**Files:**
- Modify: `tests/conftest.py`
- Delete: all old domain model files and their tests (listed in the File Map above)

- [ ] **Step 1: Run the full test suite to see the current state**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest -v
```

Note which tests fail due to the old `Character` import — these are the ones we are about to clean up.

- [ ] **Step 2: Replace `tests/conftest.py`**

```python
# tests/conftest.py
import pytest
from domain.models.character import Character
from domain.models.character_module import CharacterModule


@pytest.fixture
def base_character():
    return Character(player="test-player-uuid", name="Willow")


@pytest.fixture
def character_with_hp_module():
    hp_module = CharacterModule(
        definition_id="health-def-id",
        values={"max_hp": 45, "current_hp": 45, "temp_hp": 0},
    )
    return Character(player="test-player-uuid", name="Willow", modules=[hp_module])
```

- [ ] **Step 3: Delete the old model files**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git rm \
  src/domain/models/alignment.py \
  src/domain/models/attack.py \
  src/domain/models/attribute.py \
  src/domain/models/background.py \
  src/domain/models/character_class.py \
  src/domain/models/death_saves.py \
  src/domain/models/feature.py \
  src/domain/models/item.py \
  src/domain/models/money.py \
  src/domain/models/race.py \
  src/domain/models/skill.py \
  src/domain/models/spell.py \
  src/domain/models/spell_components.py \
  src/domain/models/spell_slots.py \
  src/domain/models/subrace.py \
  src/domain/utils/character_utils.py \
  tests/factories/character_factory.py \
  tests/unit/models/test_character.py \
  tests/unit/models/test_utils.py
```

- [ ] **Step 4: Run the full test suite to confirm all tests pass**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest -v
```

Expected: all tests in `tests/unit/models/` and `tests/unit/repositories/` pass. Zero failures.

- [ ] **Step 5: Commit**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git add tests/conftest.py && git commit -m "chore: remove old flat domain models and update conftest"
```

---

## Final verification

- [ ] **Run the complete test suite one last time**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && uv run pytest -v --tb=short
```

Expected: all tests pass, no warnings about missing imports.

- [ ] **Push to remote**

```bash
cd /Users/marthox/Dev/character-vault/services/character-manager && git push
```

- [ ] **Update the orchestrator submodule pointer**

```bash
cd /Users/marthox/Dev/character-vault && git add services/character-manager && git commit -m "Update character-manager: domain layer for module system (Plan A)"
```
