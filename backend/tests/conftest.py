import os

# Настройки для тестов выставляются ДО импорта приложения.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ARGON2_TIME_COST"] = "1"
os.environ["ARGON2_MEMORY_COST"] = "8192"
os.environ["ARGON2_PARALLELISM"] = "1"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app

STRONG = "Str0ng!Pass"


@pytest.fixture()
def client():
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(engine)


def make_user(client: TestClient, login: str, password: str = STRONG) -> dict:
    """Регистрирует пользователя, логинится и возвращает заголовок Authorization."""
    assert client.post("/api/register", json={"login": login, "password": password}).status_code == 201
    token = client.post("/api/login", json={"login": login, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
