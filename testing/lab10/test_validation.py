"""Тесты валидации и негативных сценариев."""


def test_short_subject_422(client, users, category_id):
    """Валидация: тема короче 3 символов — 422."""
    r = client.post("/api/requests", headers=users["applicant"], json={
        "subject": "ab", "description": "нормальное описание", "category_id": category_id})
    assert r.status_code == 422
    assert r.json()["detail"] == "Ошибка валидации данных"
    assert r.json()["errors"]


def test_empty_description_422(client, users, category_id):
    """Валидация: пустое описание — 422."""
    r = client.post("/api/requests", headers=users["applicant"], json={
        "subject": "Нормальная тема", "description": "", "category_id": category_id})
    assert r.status_code == 422


def test_invalid_priority_422(client, users, category_id):
    """Валидация: неизвестный приоритет — 422."""
    r = client.post("/api/requests", headers=users["applicant"], json={
        "subject": "Нормальная тема", "description": "описание",
        "category_id": category_id, "priority": "super"})
    assert r.status_code == 422


def test_subject_max_length_boundary(client, users, category_id):
    """Граница: тема 200 символов — 201, 201 символ — 422."""
    r = client.post("/api/requests", headers=users["applicant"], json={
        "subject": "Д" * 200, "description": "граница", "category_id": category_id})
    assert r.status_code == 201
    r = client.post("/api/requests", headers=users["applicant"], json={
        "subject": "Д" * 201, "description": "за границей", "category_id": category_id})
    assert r.status_code == 422


def test_missing_category_rejected(client, users):
    """Негатив: несуществующая категория при создании отклоняется (400)."""
    r = client.post("/api/requests", headers=users["applicant"], json={
        "subject": "Нормальная тема", "description": "описание", "category_id": 99999})
    assert r.status_code == 400
    assert "detail" in r.json()
