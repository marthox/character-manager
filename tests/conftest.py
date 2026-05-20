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
