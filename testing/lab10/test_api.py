"""Тесты REST API: успешные запросы, ошибочный ввод, отсутствующий ресурс, коды."""


def test_create_and_get_request(client, users, new_ticket):
    """API: POST возвращает 201 и созданную заявку, GET — 200 и те же данные."""
    num = new_ticket["number"]
    assert num.startswith("З-")
    r = client.get(f"/api/requests/{num}", headers=users["applicant"])
    assert r.status_code == 200
    body = r.json()
    assert body["number"] == num
    assert body["subject"] == "Автотест: тестовая заявка"


def test_list_requests_ok(client, users):
    """API: GET /api/requests — 200 и JSON-массив."""
    r = client.get("/api/requests", headers=users["operator"])
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_missing_request_404(client, admin_h):
    """API: запрос несуществующей заявки — 404 с единым форматом ошибки."""
    r = client.get("/api/requests/З-999999", headers=admin_h)
    assert r.status_code == 404
    assert "detail" in r.json()


def test_unauthenticated_401(client):
    """API: обращение без токена — 401."""
    r = client.get("/api/requests")
    assert r.status_code == 401


def test_delete_request_204_then_404(client, admin_h, users, new_ticket):
    """API: DELETE администратором — 204, повторный GET — 404."""
    num = new_ticket["number"]
    r = client.delete(f"/api/requests/{num}", headers=admin_h)
    assert r.status_code == 204
    r = client.get(f"/api/requests/{num}", headers=admin_h)
    assert r.status_code == 404


def test_delete_forbidden_for_applicant(client, users, new_ticket):
    """API: DELETE заявителем — 403."""
    r = client.delete(f"/api/requests/{new_ticket['number']}", headers=users["applicant"])
    assert r.status_code == 403


def test_references_endpoints(client, users):
    """API: справочники /statuses, /categories, /priorities — 200."""
    for path, check in [("/api/statuses", lambda b: "transitions" in b),
                        ("/api/categories", lambda b: isinstance(b, list) and len(b) >= 4),
                        ("/api/priorities", lambda b: isinstance(b, dict) or isinstance(b, list))]:
        r = client.get(path, headers=users["applicant"])
        assert r.status_code == 200, path
        assert check(r.json()), path
