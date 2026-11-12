from conftest import make_user


def create_resource(client, headers, title="Секретный отчёт"):
    r = client.post("/api/resources", json={"title": title, "content": "данные"}, headers=headers)
    assert r.status_code == 201
    return r.json()["id"]


def grant(client, headers, rid, login, **flags):
    body = {"login": login, "can_read": False, "can_update": False, "can_delete": False, **flags}
    return client.put(f"/api/resources/{rid}/permissions", json=body, headers=headers)


def test_owner_has_full_access(client):
    alice = make_user(client, "alice")
    rid = create_resource(client, alice)
    assert client.get(f"/api/resources/{rid}", headers=alice).status_code == 200
    assert client.put(f"/api/resources/{rid}", json={"title": "N", "content": "x"}, headers=alice).status_code == 200
    assert client.delete(f"/api/resources/{rid}", headers=alice).status_code == 204


def test_user_without_permission_is_denied(client):
    alice, carol = make_user(client, "alice"), make_user(client, "carol")
    rid = create_resource(client, alice)
    r = client.get(f"/api/resources/{rid}", headers=carol)
    assert r.status_code == 403
    assert "данные" not in r.text
    assert client.put(f"/api/resources/{rid}", json={"title": "x", "content": ""}, headers=carol).status_code == 403
    assert client.delete(f"/api/resources/{rid}", headers=carol).status_code == 403


def test_owner_grants_read_to_another_user(client):
    alice, bob = make_user(client, "alice"), make_user(client, "bob")
    rid = create_resource(client, alice)
    assert client.get(f"/api/resources/{rid}", headers=bob).status_code == 403  # до выдачи права

    assert grant(client, alice, rid, "bob", can_read=True).status_code == 200
    assert client.get(f"/api/resources/{rid}", headers=bob).status_code == 200  # после выдачи

    # выдано только чтение — изменение и удаление по-прежнему запрещены
    assert client.put(f"/api/resources/{rid}", json={"title": "x", "content": ""}, headers=bob).status_code == 403
    assert client.delete(f"/api/resources/{rid}", headers=bob).status_code == 403


def test_granted_update_and_delete_work_and_revoke_works(client):
    alice, bob = make_user(client, "alice"), make_user(client, "bob")
    rid = create_resource(client, alice)
    grant(client, alice, rid, "bob", can_update=True, can_delete=True)
    assert client.put(f"/api/resources/{rid}", json={"title": "N", "content": "y"}, headers=bob).status_code == 200
    grant(client, alice, rid, "bob")  # отзыв всех прав
    assert client.delete(f"/api/resources/{rid}", headers=bob).status_code == 403


def test_only_owner_can_grant(client):
    alice, bob, carol = make_user(client, "alice"), make_user(client, "bob"), make_user(client, "carol")
    rid = create_resource(client, alice)
    grant(client, alice, rid, "bob", can_read=True)
    # bob (даже с правом чтения) и carol не могут выдавать права, в т.ч. себе
    assert grant(client, bob, rid, "carol", can_read=True).status_code == 403
    assert grant(client, carol, rid, "carol", can_read=True, can_delete=True).status_code == 403
    assert client.get(f"/api/resources/{rid}", headers=carol).status_code == 403


def test_list_shows_only_own_and_shared(client):
    alice, bob, carol = make_user(client, "alice"), make_user(client, "bob"), make_user(client, "carol")
    rid = create_resource(client, alice)
    grant(client, alice, rid, "bob", can_read=True)
    assert [x["id"] for x in client.get("/api/resources", headers=bob).json()] == [rid]
    assert client.get("/api/resources", headers=carol).json() == []


def test_requires_authentication(client):
    alice = make_user(client, "alice")
    rid = create_resource(client, alice)
    assert client.get(f"/api/resources/{rid}").status_code == 401
    assert client.get(f"/api/resources/{rid}", headers={"Authorization": "Bearer fake"}).status_code == 401
    assert client.get("/api/resources/9999", headers=alice).status_code == 404
