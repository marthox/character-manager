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
