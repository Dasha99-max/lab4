import logging

import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from conftest import STRONG


def full_log(caplog) -> str:
    """Текст сообщений + структурированные поля (extra) всех записей лога."""
    return caplog.text + " ".join(str(getattr(r, "fields", "")) for r in caplog.records)


def test_register_success(client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    r = client.post("/api/register", json={"login": "alice", "password": STRONG})
    assert r.status_code == 201
    assert r.json() == {"message": "user создан"}

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.login == "alice"))
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")  # хэш Argon2id с солью
    assert STRONG not in user.password_hash
    assert "user_registered" in caplog.text
    assert STRONG not in full_log(caplog)  # пароль не логируется


def test_register_duplicate_login(client, caplog):
    caplog.set_level(logging.INFO, logger="app")
    assert client.post("/api/register", json={"login": "bob", "password": STRONG}).status_code == 201
    r = client.post("/api/register", json={"login": "bob", "password": STRONG})
    assert r.status_code == 409
    assert "занят" in r.json()["detail"]
    assert "register_login_taken" in caplog.text


@pytest.mark.parametrize(
    "password",
    ["Sh0rt!a", "alllower1!", "ALLUPPER1!", "NoDigits!!", "NoSpecial123"],
)
def test_register_weak_password(client, caplog, password):
    caplog.set_level(logging.INFO, logger="app")
    r = client.post("/api/register", json={"login": "carol", "password": password})
    assert r.status_code == 422
    assert "пароль" in r.json()["detail"].lower()
    assert password not in r.text  # пароль не возвращается в ответе
    assert "validation_error" in caplog.text
    assert password not in full_log(caplog)  # и не попадает в лог


@pytest.mark.parametrize("login", ["ab", "a" * 33, "bad login", "юзер123", "a@b.c"])
def test_register_invalid_login(client, login):
    r = client.post("/api/register", json={"login": login, "password": STRONG})
    assert r.status_code == 422


def test_same_password_gives_different_hashes(client):
    client.post("/api/register", json={"login": "user1", "password": STRONG})
    client.post("/api/register", json={"login": "user2", "password": STRONG})
    with SessionLocal() as db:
        hashes = [u.password_hash for u in db.scalars(select(User))]
    assert len(set(hashes)) == 2  # разная соль
