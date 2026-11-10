"""Тесты бизнес-логики: переходы статусов, права ролей, назначение исполнителя."""


def test_status_chain_take_complete_close(client, users, new_ticket):
    """Бизнес-логика: заявка проходит цепочку Новая → В работе → Выполнена → Закрыта."""
    num = new_ticket["number"]
    assert new_ticket["status"] == "new"

    r = client.post(f"/api/requests/{num}/take", headers=users["executor"])
    assert r.status_code == 200 and r.json()["status"] == "in_work"

    r = client.post(f"/api/requests/{num}/complete", headers=users["executor"],
                    json={"text": "работа сделана"})
    assert r.status_code == 200 and r.json()["status"] == "done"

    r = client.post(f"/api/requests/{num}/close", headers=users["applicant"])
    assert r.status_code == 200 and r.json()["status"] == "closed"


def test_invalid_status_transition_rejected(client, users, new_ticket):
    """Бизнес-логика: недопустимый переход (закрыть новую заявку) отклоняется с 400."""
    r = client.post(f"/api/requests/{new_ticket['number']}/close", headers=users["operator"])
    assert r.status_code == 400
    assert "detail" in r.json()


def test_complete_without_take_rejected(client, users, new_ticket, admin_h):
    """Бизнес-логика: выполнить можно только заявку в работе (иначе 400)."""
    r = client.get("/api/users", headers=admin_h)
    executor_id = next(u["id"] for u in r.json() if u["username"] == "t_executor")
    client.patch(f"/api/requests/{new_ticket['number']}",
                 headers=users["operator"], json={"executor_id": executor_id})
    r = client.post(f"/api/requests/{new_ticket['number']}/complete",
                    headers=users["executor"], json={"text": "преждевременно"})
    assert r.status_code == 400


def test_complete_unassigned_executor_forbidden(client, users, new_ticket):
    """Роли: исполнитель не может выполнить чужую (не назначенную ему) заявку — 403."""
    r = client.post(f"/api/requests/{new_ticket['number']}/complete",
                    headers=users["executor"], json={"text": "чужая заявка"})
    assert r.status_code == 403


def test_executor_cannot_create_ticket(client, users, category_id):
    """Роли: исполнителю запрещено подавать заявки (403)."""
    r = client.post("/api/requests", headers=users["executor"], json={
        "subject": "Попытка исполнителя", "description": "не должно создаться",
        "category_id": category_id})
    assert r.status_code == 403


def test_applicant_sees_only_own_tickets(client, users, new_ticket):
    """Роли: заявитель в списке видит только свои заявки."""
    r = client.get("/api/requests", headers=users["applicant"])
    assert r.status_code == 200
    tickets = r.json()
    assert len(tickets) > 0
    assert all(t["applicant_name"] == "Тест Заявитель" for t in tickets)


def test_operator_assigns_executor(client, users, new_ticket, admin_h):
    """Бизнес-логика: оператор назначает исполнителя, он сохраняется в заявке."""
    r = client.get("/api/users", headers=admin_h)
    executor_id = next(u["id"] for u in r.json() if u["username"] == "t_executor")
    r = client.patch(f"/api/requests/{new_ticket['number']}",
                     headers=users["operator"], json={"executor_id": executor_id})
    assert r.status_code == 200
    assert r.json()["executor_name"] == "Тест Исполнитель"
