# -*- coding: utf-8 -*-
"""Проверка REST API (ЛР №7, п. 8–9): выполняет 14 запросов по контракту,
сохраняет команды и ответы в docs/api_checks.txt и коллекцию Postman
в docs/postman_collection.json. Приложение должно быть запущено."""
import json
import os
import urllib.request
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "http://localhost:8000/api"


def call(method, path, token=None, data=None, form=None):
    req = urllib.request.Request(BASE + urllib.parse.quote(path, safe="/?=&"), method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode()
        req.add_header("Content-Type", "application/json")
    elif form is not None:
        body = urllib.parse.urlencode(form).encode()
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, body) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")


def curl(method, path, token=True, data=None, form=None):
    parts = [f"curl -X {method} http://localhost:8000/api{path}"]
    if token:
        parts.append('  -H "Authorization: Bearer $TOKEN"')
    if data is not None:
        parts.append('  -H "Content-Type: application/json"')
        parts.append(f"  -d '{json.dumps(data, ensure_ascii=False)}'")
    if form is not None:
        parts.append("  -d " + " -d ".join(f'"{k}={v}"' for k, v in form.items()))
    return " \\\n".join(parts)


def brief(res, limit=400):
    s = json.dumps(res, ensure_ascii=False, indent=1)
    return s if len(s) <= limit else s[:limit] + "\n  ... (усечено)"


def main():
    out = ["Проверка REST API — ЛР №7", "=" * 70, ""]
    checks = []

    def step(title, method, path, token=None, data=None, form=None, expect=None):
        st, res = call(method, path, token=token, data=data, form=form)
        mark = "OK " if expect is None or st == expect else "!!!"
        out.append(f"### {title}")
        out.append(curl(method, path, token=token is not None, data=data, form=form))
        out.append(f"-> HTTP {st} [{mark}ожидали {expect or st}]")
        out.append(brief(res))
        out.append("")
        checks.append(st)

    # Авторизация
    st, res = call("POST", "/auth/login", form={"username": "admin", "password": "admin123"})
    token = res["access_token"]
    out += ["### 1. Авторизация (получение JWT)",
            curl("POST", "/auth/login", token=False,
                 form={"username": "admin", "password": "admin123"}),
            f"-> HTTP {st}, получен access_token", ""]

    step("2. GET /requests — список заявок", "GET", "/requests", token=token, expect=200)
    step("3. GET /requests с фильтрами и поиском", "GET",
         "/requests?status=new&priority=high&q=1С", token=token, expect=200)
    st, created = call("POST", "/requests", token=token, data={
        "subject": "Тестовая заявка API", "description": "Создана из api_checks.py",
        "priority": "low", "category_id": 1})
    num = created["number"]
    out += ["### 4. POST /requests — создание заявки",
            curl("POST", "/requests", data={
                "subject": "Тестовая заявка API", "description": "Создана из api_checks.py",
                "priority": "low", "category_id": 1}),
            f"-> HTTP {st}, создана {num}", brief(created), ""]
    checks.append(st)
    step(f"5. GET /requests/{num} — одна заявка", "GET", f"/requests/{num}", token=token, expect=200)
    step("6. GET /requests/З-999999 — несуществующая -> 404", "GET",
         "/requests/З-999999", token=token, expect=404)
    step(f"7. PATCH /requests/{num} — смена приоритета", "PATCH",
         f"/requests/{num}", token=token, data={"priority": "high"}, expect=200)
    step("8. POST /requests с невалидными данными -> 422", "POST", "/requests",
         token=token, data={"subject": "xy"}, expect=422)
    step(f"9. POST /requests/{num}/comments — комментарий", "POST",
         f"/requests/{num}/comments", token=token, data={"text": "Комментарий через API"}, expect=201)
    step("10. GET /statuses — справочник статусов", "GET", "/statuses", token=token, expect=200)
    step("11. GET /categories — справочник категорий", "GET", "/categories", token=token, expect=200)
    step("12. GET /users — список пользователей (admin)", "GET", "/users", token=token, expect=200)
    step("13. GET /users без токена -> 401", "GET", "/users", expect=401)
    step(f"14. DELETE /requests/{num} — удаление -> 204", "DELETE",
         f"/requests/{num}", token=token, expect=204)

    ok = len(checks)
    out.append(f"Выполнено запросов: {ok}")

    with open(os.path.join(ROOT, "docs", "api_checks.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("docs/api_checks.txt записан")

    # --- Postman collection ---
    def item(name, method, path, data=None, auth=True):
        it = {"name": name,
              "request": {"method": method, "header": [], "url": {
                  "raw": "{{base_url}}/api" + path,
                  "host": ["{{base_url}}"], "path": ["api"] + [p for p in path.split("/") if p]}}}
        if auth:
            it["request"]["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}"}]}
        if data is not None:
            it["request"]["header"].append({"key": "Content-Type", "value": "application/json"})
            it["request"]["body"] = {"mode": "raw", "raw": json.dumps(data, ensure_ascii=False, indent=2)}
        return it

    collection = {
        "info": {"name": "Система учёта заявок — REST API (ЛР7)",
                 "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "variable": [
            {"key": "base_url", "value": "http://localhost:8000"},
            {"key": "token", "value": "<вставьте access_token из /api/auth/login>"}],
        "item": [
            item("Логин (получить токен)", "POST", "/auth/login", auth=False),
            item("Список заявок", "GET", "/requests"),
            item("Список с фильтрами", "GET", "/requests?status=new&priority=high&q=1С"),
            item("Создать заявку", "POST", "/requests",
                 {"subject": "Тема заявки", "description": "Описание", "priority": "medium", "category_id": 1}),
            item("Получить заявку", "GET", "/requests/З-000001"),
            item("Изменить заявку", "PATCH", "/requests/З-000001", {"priority": "high"}),
            item("Взять в работу", "POST", "/requests/З-000001/take"),
            item("Отметить выполненной", "POST", "/requests/З-000001/complete"),
            item("Закрыть заявку", "POST", "/requests/З-000001/close"),
            item("Комментарий", "POST", "/requests/З-000001/comments", {"text": "Текст"}),
            item("Удалить заявку", "DELETE", "/requests/З-000001"),
            item("Статусы", "GET", "/statuses"),
            item("Приоритеты", "GET", "/priorities"),
            item("Категории", "GET", "/categories"),
            item("Пользователи (admin)", "GET", "/users"),
        ],
    }
    with open(os.path.join(ROOT, "docs", "postman_collection.json"), "w", encoding="utf-8") as f:
        json.dump(collection, f, ensure_ascii=False, indent=2)
    print("docs/postman_collection.json записан")


if __name__ == "__main__":
    main()
