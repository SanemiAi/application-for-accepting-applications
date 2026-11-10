"""Регрессионные тесты на дефекты BUG-01..BUG-03 из testing/lab9/bug_reports.md."""


def _login_web(client, username="admin", password="admin123"):
    r = client.post("/login", data={"username": username, "password": password},
                    follow_redirects=False)
    assert r.status_code == 303


def test_search_empty_filters_ok(client):
    """BUG-01: поиск с пустыми значениями фильтров (форма браузера) не должен давать 422.

    Утверждение выявляет дефект: до исправления такой запрос возвращал HTTP 422
    «Ошибка валидации данных» вместо страницы со списком.
    """
    _login_web(client)
    r = client.get("/?q=тест&status=&category_id=&priority=")
    assert r.status_code == 200
    assert "Заявки" in r.text


def test_search_by_category_name(client, admin_h, category_id):
    """BUG-02: поиск находит заявки по названию категории."""
    r = client.get("/api/admin/categories", headers=admin_h)
    cat_name = r.json()[0]["name"]
    client.post("/api/requests", headers=admin_h, json={
        "subject": "Регрессия BUG-02", "description": "поиск по категории",
        "category_id": category_id})
    r = client.get("/api/requests", headers=admin_h, params={"q": cat_name})
    assert r.status_code == 200
    assert any(t["category_name"] == cat_name for t in r.json())


def test_openapi_token_url(client):
    """BUG-03: схема безопасности OpenAPI указывает верный tokenUrl (/api/auth/login),
    чтобы кнопка Authorize в Swagger UI выдавала токен."""
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schemes = r.json()["components"]["securitySchemes"]
    flows = [s for s in schemes.values() if s.get("type") == "oauth2"]
    assert flows, "oauth2-схема не найдена"
    token_url = flows[0]["flows"]["password"]["tokenUrl"]
    assert token_url == "/api/auth/login", token_url


def test_search_special_chars_no_error(client):
    """Регрессия на устойчивость поиска: спецсимволы не ломают страницу."""
    _login_web(client)
    r = client.get("/?q=%27%3Cscript%3E%25")
    assert r.status_code == 200
