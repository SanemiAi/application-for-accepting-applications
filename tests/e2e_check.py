import json
import urllib.request
import urllib.parse

BASE = "http://localhost:8000"
ok, fail = 0, 0


def check(name, cond, extra=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name} {extra}")


def api(method, path, token=None, data=None, form=None):
    req = urllib.request.Request(BASE + "/api" + urllib.parse.quote(path, safe="/?=&"), method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    elif form is not None:
        body = urllib.parse.urlencode(form).encode()
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, body) as r:
            raw = r.read()
            if r.headers.get("Content-Type", "").startswith("application/json") and raw:
                return r.status, json.loads(raw)
            return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(NoRedirect)


def web(method, path, cookie=None, form=None):
    req = urllib.request.Request(BASE + urllib.parse.quote(path, safe="/?=&"), method=method)
    if cookie:
        req.add_header("Cookie", cookie)
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        r = opener.open(req, body)
        content = r.read().decode("utf-8")
        return r.status, r.headers, content
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8", errors="replace")
        return e.code, e.headers, content


def web_login(username, password):
    st, h, _ = web("POST", "/login", form={"username": username, "password": password})
    if st == 303 and "access_token=" in h.get("Set-Cookie", ""):
        return h["Set-Cookie"].split(";")[0]
    return None


print("== 1. Категории (нужно >= 4) ==")
st, tk = api("POST", "/auth/login", form={"username": "admin", "password": "admin123"})
admin = tk["access_token"]
st, users = api("GET", "/admin/users", token=admin)
check("Админ авторизован, список пользователей", st == 200)
st, cats = api("GET", "/admin/categories", token=admin)
check(f"Категорий >= 4 (сейчас {len(cats) if isinstance(cats, list) else '?'})", isinstance(cats, list) and len(cats) >= 4, cats)

print("== 2. Создание пользователей ролей ==")
for u, p, n, r in [("ivan", "ivan123", "Иван Петров", "applicant"),
                   ("olga", "olga123", "Ольга Сидорова", "operator"),
                   ("igor", "igor123", "Игорь Мастеров", "executor")]:
    st, res = api("POST", "/admin/users", token=admin,
                  data={"username": u, "password": p, "full_name": n, "role": r})
    exists = st == 400 and "существует" in str(res)
    check(f"Создан {u} ({r})", st in (200, 201) or exists, res)

st, users = api("GET", "/admin/users", token=admin)
uid = {u["username"]: u["id"] for u in users}

print("== 3. Заявитель создаёт заявку (API, с приоритетом) ==")
st, tk = api("POST", "/auth/login", form={"username": "ivan", "password": "ivan123"})
ivan = tk["access_token"]
st, t = api("POST", "/requests", token=ivan,
            data={"subject": "Не работает принтер", "description": "Принтер HP в бухгалтерии не печатает.",
                  "category_id": cats[0]["id"], "priority": "high"})
check("Заявка создана, номер присвоен", st == 201 and t["number"].startswith("З-"), t)
check("Приоритет сохранён", t.get("priority") == "high" and t.get("priority_label") == "Высокий", t.get("priority"))
num = t["number"]

st, res = api("POST", "/requests", token=ivan,
              data={"subject": "аб", "description": "короткая тема"})
check("Валидация: короткая тема -> 422", st == 422, st)
st, res = api("POST", "/requests", token=ivan,
              data={"subject": "Нормальная тема", "description": "описание", "priority": "super"})
check("Валидация: неверный приоритет -> 422", st == 422, st)

print("== 4. Веб: фильтры и поиск ==")
adm_cookie = web_login("admin", "admin123")
check("Веб-логин админа", adm_cookie is not None)
st, _, html = web("GET", "/?status=new", cookie=adm_cookie)
check("Фильтр по статусу: заявка видна", st == 200 and num in html)
st, _, html = web("GET", "/?status=closed", cookie=adm_cookie)
check("Фильтр по статусу: closed пуст", st == 200 and num not in html)
st, _, html = web("GET", "/?q=принтер", cookie=adm_cookie)
check("Поиск по теме находит заявку", st == 200 and num in html)
st, _, html = web("GET", "/?q=бухгалтерии", cookie=adm_cookie)
check("Поиск по описанию находит заявку", st == 200 and num in html)
st, _, html = web("GET", "/?priority=high&status=new", cookie=adm_cookie)
check("Фильтр по приоритету работает", st == 200 and num in html)
st, _, html = web("GET", "/?priority=low&status=new", cookie=adm_cookie)
check("Фильтр по приоритету: low не содержит high-заявку", st == 200 and num not in html)
st, _, html = web("GET", "/?q=несуществующийтекст", cookie=adm_cookie)
check("Поиск: пустое состояние", st == 200 and "ничего не найдено" in html)

print("== 5. Оператор назначает исполнителя (веб) ==")
olga_cookie = web_login("olga", "olga123")
check("Веб-логин оператора", olga_cookie is not None)
st, h, _ = web("POST", f"/tickets/{num}/assign", cookie=olga_cookie, form={"executor_id": str(uid["igor"])})
check("Назначение исполнителя -> 303", st == 303, (st, h))
st, _, html = web("GET", f"/tickets/{num}", cookie=olga_cookie)
check("Исполнитель отображается в карточке", "Игорь Мастеров" in html)

print("== 6. Оператор редактирует заявку (веб) ==")
st, _, html = web("GET", f"/tickets/{num}/edit", cookie=olga_cookie)
check("Страница редактирования открывается", st == 200 and "Редактирование" in html)
st, _, _ = web("POST", f"/tickets/{num}/edit", cookie=olga_cookie,
               form={"subject": "Не работает принтер HP LaserJet", "description": "Принтер HP LaserJet в бухгалтерии не печатает. Уточнено оператором.", "category_id": str(cats[0]["id"])})
st, t = api("GET", f"/requests/{num}", token=admin)
check("Тема уточнена оператором", t["subject"] == "Не работает принтер HP LaserJet", t["subject"])

print("== 7. Исполнитель берёт в работу и выполняет (веб) ==")
igor_cookie = web_login("igor", "igor123")
check("Веб-логин исполнителя", igor_cookie is not None)
st, _, html = web("GET", "/", cookie=igor_cookie)
check("Исполнитель видит назначенную заявку", num in html)
st, _, _ = web("POST", f"/tickets/{num}/take", cookie=igor_cookie)
st, t = api("GET", f"/requests/{num}", token=admin)
check("Статус 'В работе'", t["status"] == "in_work", t["status"])
st, _, _ = web("POST", f"/tickets/{num}/complete", cookie=igor_cookie, form={"text": "Заменён картридж, принтер работает."})
st, t = api("GET", f"/requests/{num}", token=admin)
check("Статус 'Выполнена'", t["status"] == "done", t["status"])

print("== 8. Заявитель дополняет описание и закрывает (веб) ==")
ivan_cookie = web_login("ivan", "ivan123")
st, _, _ = web("POST", f"/tickets/{num}/edit", cookie=ivan_cookie, form={"description": "Проверил печать — всё работает, спасибо!"})
st, t = api("GET", f"/requests/{num}", token=admin)
check("Описание дополнено заявителем", "[Дополнено заявителем]" in t["description"])
st, _, _ = web("POST", f"/tickets/{num}/close", cookie=ivan_cookie)
st, t = api("GET", f"/requests/{num}", token=admin)
check("Заявка закрыта заявителем", t["status"] == "closed", t["status"])

print("== 9. Запрещённые переходы и доступ ==")
st, _, html = web("POST", f"/tickets/{num}/complete", cookie=igor_cookie)
st2, _, html2 = web("GET", f"/tickets/{num}?error=x", cookie=igor_cookie)
st, t = api("GET", f"/requests/{num}", token=admin)
check("Закрытую нельзя выполнить снова", t["status"] == "closed")
st, res = api("GET", f"/requests/{num}", token=None)
check("Без токена API -> 401", st == 401, st)
st, h, html = web("GET", f"/tickets/{num}", cookie=igor_cookie)
check("Исполнитель видит свою закрытую заявку", st == 200 and num in html)
st, tk = api("POST", "/auth/login", form={"username": "ivan", "password": "ivan123"})
st, res = api("GET", "/admin/users", token=tk["access_token"])
check("Заявителю запрещён /admin -> 403", st == 403, st)

print("== 10. Страницы ошибок и удаление ==")
st, _, html = web("GET", "/tickets/З-999999", cookie=adm_cookie)
check("Несуществующая заявка -> HTML 404", st == 404 and "не найдена" in html.lower(), st)
st, res = api("DELETE", f"/requests/{num}", token=tk["access_token"])
check("Удаление заявителем -> 403", st == 403, st)
st, res = api("DELETE", f"/requests/{num}", token=admin)
check("Удаление администратором -> 204", st == 204, st)
st, res = api("GET", f"/requests/{num}", token=admin)
check("Удалённая заявка не находится -> 404", st == 404, st)
st, res = api("DELETE", f"/requests/{num}", token=admin)
check("Повторное удаление -> 404", st == 404, st)

print("== 11. Тестовые данные (ЛР6): >=10 заявок, >=4 пользователей ==")
st, lst = api("GET", "/requests", token=admin)
check(f"Заявок >= 10 (сейчас {len(lst)})", len(lst) >= 10, len(lst))
st, users = api("GET", "/admin/users", token=admin)
check(f"Пользователей >= 4 (сейчас {len(users)})", len(users) >= 4, len(users))
check("Категорий >= 4", len(cats) >= 4, len(cats))
statuses = {t["status"] for t in lst}
check(f"Несколько статусов в данных ({sorted(statuses)})", len(statuses) >= 3, statuses)

print(f"\nИТОГ: {ok} passed, {fail} failed")
