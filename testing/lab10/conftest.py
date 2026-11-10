"""Фикстуры автотестов ЛР №10: приложение на ОТДЕЛЬНОЙ тестовой БД (SQLite-файл).

Реальная PostgreSQL-база не затрагивается: DATABASE_URL подменяется до импорта
приложения, таблицы и стартовые данные создаются в testing/lab10/test_tickets.db.

Запуск: python -m pytest testing/lab10 -v
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

TEST_DB = Path(__file__).parent / "test_tickets.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin123"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    if TEST_DB.exists():
        TEST_DB.unlink()
    with TestClient(app) as c:  # startup: create_all + миграция + сид admin/категорий
        yield c
    # файл тестовой БД удаляется при следующем запуске (Windows держит lock)


def _token(client, username, password):
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin_h(client):
    return _token(client, "admin", "admin123")


@pytest.fixture(scope="session")
def users(client, admin_h):
    """Пользователи всех ролей для тестов."""
    created = {}
    for username, password, full_name, role in [
        ("t_applicant", "pass12345", "Тест Заявитель", "applicant"),
        ("t_operator", "pass12345", "Тест Оператор", "operator"),
        ("t_executor", "pass12345", "Тест Исполнитель", "executor"),
    ]:
        client.post("/api/admin/users", headers=admin_h,
                    json={"username": username, "password": password,
                          "full_name": full_name, "role": role})
        created[role] = _token(client, username, password)
    return created


@pytest.fixture(scope="session")
def category_id(client, admin_h):
    r = client.get("/api/admin/categories", headers=admin_h)
    return r.json()[0]["id"]


@pytest.fixture()
def new_ticket(client, users, category_id):
    """Свежая заявка от тестового заявителя; возвращает dict ответа."""
    r = client.post("/api/requests", headers=users["applicant"], json={
        "subject": "Автотест: тестовая заявка",
        "description": "Создана автотестом ЛР10",
        "category_id": category_id,
        "priority": "medium",
    })
    assert r.status_code == 201, r.text
    return r.json()
