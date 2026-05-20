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
    templates_resp = client.get("/templates")
    template_id = templates_resp.json()[0]["id"]

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
    templates_resp = client.get("/templates")
    template_id = templates_resp.json()[0]["id"]
    create_resp = client.post(
        "/characters",
        json={"player": "player-2", "name": "Gandalf", "template_id": template_id},
    )
    char_id = create_resp.json()["id"]

    response = client.get(f"/characters/{char_id}")
    assert response.status_code == 200
    char = response.json()
    assert char["name"] == "Gandalf"
    assert len(char["modules"]) == 11

    modules_resp = client.get(f"/characters/{char_id}/modules")
    modules = modules_resp.json()
    health_mod = next(
        m for m in modules if "max_hp" in m["values"]
    )
    assert health_mod["values"]["max_hp"] == 10
    assert health_mod["values"]["current_hp"] == 10


def test_update_character_hp(client):
    templates_resp = client.get("/templates")
    template_id = templates_resp.json()[0]["id"]
    create_resp = client.post(
        "/characters",
        json={"player": "player-3", "name": "Legolas", "template_id": template_id},
    )
    char = create_resp.json()
    char_id = char["id"]

    modules_resp = client.get(f"/characters/{char_id}/modules")
    modules = modules_resp.json()
    health_mod = next(m for m in modules if "max_hp" in m["values"])
    mod_id = health_mod["id"]

    update_resp = client.patch(
        f"/characters/{char_id}/modules/{mod_id}",
        json={"values": {"max_hp": 45, "current_hp": 38, "temp_hp": 5}},
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["values"]["max_hp"] == 45
    assert updated["values"]["current_hp"] == 38
    assert updated["values"]["temp_hp"] == 5

    verify_resp = client.get(f"/characters/{char_id}/modules/{mod_id}")
    assert verify_resp.json()["values"]["current_hp"] == 38


def test_add_custom_module_to_character(client):
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

    char_resp = client.post(
        "/characters", json={"player": "player-4", "name": "Investigator"}
    )
    char_id = char_resp.json()["id"]

    add_resp = client.post(
        f"/characters/{char_id}/modules",
        json={"definition_id": custom_mod_id, "values": {"max_sanity": 80, "current_sanity": 75}},
    )
    assert add_resp.status_code == 201
    added = add_resp.json()
    assert added["values"]["max_sanity"] == 80


def test_category_uniqueness_constraint(client):
    templates_resp = client.get("/templates")
    template_id = templates_resp.json()[0]["id"]
    char_resp = client.post(
        "/characters",
        json={"player": "player-5", "name": "Fighter", "template_id": template_id},
    )
    char_id = char_resp.json()["id"]

    modules_resp = client.get("/modules")
    health_mod = next(m for m in modules_resp.json() if m["category"] == "health")

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
    assert len(chars) >= 2
    assert all(c["player"] == "filter-player" for c in chars)
