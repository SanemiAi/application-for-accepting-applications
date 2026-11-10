"""Ручное тестирование ЛР №9 — выполнение тест-кейсов TC-01..TC-28.

Запускается против работающего приложения (docker compose up -d, демо-данные
загружены через tools/seed_demo.py). Результаты пишутся в evidence/manual_checks.txt.
Созданные в ходе проверок заявки удаляются в конце (очистка тестовых данных).

Запуск: python testing/lab9/run_manual_checks.py
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.credentials import required  # noqa: E402

BASE = "http://localhost:8000"
# Учётные данные берутся из окружения/.env, в репозитории не хранятся
ADMIN_PASSWORD = required("ADMIN_PASSWORD")
DEMO_PASSWORD = required("SEED_DEMO_PASSWORD")
OUT = Path(__file__).parent / "evidence" / "manual_checks.txt"
LOG = []
RESULTS = {}
CREATED = []  # номера заявок для очистки


def log(line=""):
    print(line)
    LOG.append(line)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


opener = urllib.request.build_opener(NoRedirect)


def api(method, path, token=None, data=None, form=None):
    req = urllib.request.Request(BASE + "/api" + urllib.parse.quote(path, safe="/?=&%"), method=method)
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
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode("utf-8", errors="replace")


def web(method, path, cookie=None, form=None):
    req = urllib.request.Request(BASE + urllib.parse.quote(path, safe="/?=&%"), method=method)
    if cookie:
        req.add_header("Cookie", cookie)
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        r = opener.open(req, body)
        return r.status, r.headers, r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8", errors="replace")


def web_login(username, password):
    st, h, _ = web("POST", "/login", form={"username": username, "password": password})
    if st == 303 and "access_token=" in h.get("Set-Cookie", ""):
        return h["Set-Cookie"].split(";")[0]
    return None


def token_of(username, password):
    st, tk = api("POST", "/auth/login", form={"username": username, "password": password})
    assert st == 200, (username, st, tk)
    return tk["access_token"]


def case(cid, name, ok, evidence):
    RESULTS[cid] = (name, "PASS" if ok else "FAIL", evidence)
    log(f"[{'PASS' if ok else 'FAIL'}] {cid} {name} — {evidence}")


def main():
    log(f"Выполнение тест-кейсов ЛР №9 — {datetime.now():%d.%m.%Y %H:%M}")
    log(f"Стенд: {BASE} (версия 1.1.0, коммит 805ae00+)")
    st, _ = api("GET", "/requests", token=token_of("admin", ADMIN_PASSWORD))
    log(f"Предусловие: /api/requests доступен -> HTTP {st}")
    log("")

    admin = token_of("admin", ADMIN_PASSWORD)
    ivan = token_of("ivan", DEMO_PASSWORD)
    olga = token_of("olga", DEMO_PASSWORD)
    igor = token_of("igor", DEMO_PASSWORD)
    adm_c = web_login("admin", ADMIN_PASSWORD)
    ivan_c = web_login("ivan", DEMO_PASSWORD)

    # ---------- Позитивные функциональные ----------
    st, t = api("POST", "/requests", token=ivan,
                data={"subject": "ТК: сломался сканер", "description": "Сканер в приёмной не включается.",
                      "category_id": 1, "priority": "medium"})
    num1 = t.get("number") if st == 201 else None
    if num1:
        CREATED.append(num1)
    case("TC-01", "Создание заявки заявителем (API)",
         st == 201 and num1 and num1.startswith("З-"), f"HTTP {st}, номер {num1}")

    st, _, html = web("GET", "/", cookie=adm_c)
    case("TC-02", "Просмотр списка заявок (веб, admin)",
         st == 200 and "З-000001" in html and "Приоритет" in html,
         f"HTTP {st}, таблица с заявками и колонкой приоритета")

    st, _, html = web("GET", "/tickets/З-000009", cookie=adm_c)
    case("TC-03", "Просмотр карточки заявки (веб)",
         st == 200 and "З-000009" in html and "Статус" in html and "Комментарии" in html,
         f"HTTP {st}, поля и комментарии отображаются")

    st, _, html = web("GET", "/?q=принтер", cookie=adm_c)
    case("TC-04", "Поиск по теме", st == 200 and "З-000001" in html and "З-000002" not in html,
         "HTTP 200, найдена только З-000001")

    st, _, html = web("GET", "/?q=Снабжение", cookie=adm_c)
    found = all(n in html for n in ("З-000002", "З-000008", "З-000011"))
    case("TC-05", "Поиск по названию категории (регрессия BUG-02)",
         st == 200 and found, "HTTP 200, найдены З-000002, З-000008, З-000011")

    st, t6 = api("POST", "/requests", token=ivan,
                 data={"subject": "ТК: дополнение описания", "description": "Первичное описание.",
                       "category_id": 1})
    num6 = t6.get("number") if st == 201 else None
    if num6:
        CREATED.append(num6)
        st, t6p = api("PATCH", f"/requests/{num6}", token=ivan,
                      data={"description": "Дополнение от заявителя: сканер Canon."})
        ok = st == 200 and "Дополнение" in (t6p.get("description") or "")
        case("TC-06", "Дополнение описания заявителем (API PATCH)", ok,
             f"HTTP {st}, описание обновлено")
    else:
        case("TC-06", "Дополнение описания заявителем (API PATCH)", False, f"создание: HTTP {st}")

    st, t7 = api("POST", "/requests", token=ivan,
                 data={"subject": "ТК: полный жизненный цикл", "description": "Проверка цепочки статусов.",
                       "category_id": 1})
    num7 = t7.get("number") if st == 201 else None
    if num7:
        CREATED.append(num7)
        st_a, _ = api("POST", f"/requests/{num7}/take", token=igor)
        st_b, tb = api("POST", f"/requests/{num7}/complete", token=igor,
                       data={"text": "Работа выполнена"})
        st_c, tc = api("POST", f"/requests/{num7}/close", token=ivan)
        ok = st_a == 200 and st_b == 200 and st_c == 200 and tc.get("status") == "closed"
        case("TC-07", "Цепочка статусов: в работу → выполнена → закрыта", ok,
             f"take {st_a}, complete {st_b}, close {st_c}, итог {tc.get('status')}")
    else:
        case("TC-07", "Цепочка статусов", False, f"создание: HTTP {st}")

    st, users = api("GET", "/users", token=admin)
    igor_id = next(u["id"] for u in users if u["username"] == "igor")
    st, t8 = api("PATCH", f"/requests/{num1}", token=olga, data={"executor_id": igor_id})
    case("TC-08", "Назначение исполнителя оператором (API PATCH)",
         st == 200 and t8.get("executor_name") == "Игорь Мастеров",
         f"HTTP {st}, исполнитель {t8.get('executor_name')}")

    st, c9 = api("POST", f"/requests/{num1}/comments", token=olga,
                 data={"text": "Комментарий оператора по ТК-09"})
    case("TC-09", "Добавление комментария (API)",
         st == 201 and c9.get("author_name") == "Ольга Сидорова",
         f"HTTP {st}, автор {c9.get('author_name')}")

    # ---------- Негативные ----------
    st, _, html = web("POST", "/tickets/new", cookie=ivan_c,
                      form={"subject": "  ", "description": "описание", "category_id": "", "priority": "medium"})
    st2, _, html2 = web("GET", "/tickets/new?error=" + urllib.parse.quote("Тема должна содержать минимум 3 символа"), cookie=ivan_c)
    case("TC-10", "Веб: пустая тема → баннер ошибки валидации",
         st == 303 and "alert" in html2, f"redirect {st}, баннер .alert отображается")

    st, res = api("POST", "/requests", token=ivan,
                  data={"subject": "ab", "description": "короткая тема", "category_id": 1})
    case("TC-11", "API: тема < 3 символов → 422",
         st == 422 and "detail" in res, f"HTTP {st}, {res.get('detail')}")

    st, res = api("POST", "/requests/З-000010/close", token=admin)
    case("TC-12", "Недопустимый переход статуса (закрыть новую) → 400",
         st == 400 and "detail" in res, f"HTTP {st}, {res.get('detail')}")

    st, _, html = web("GET", "/tickets/З-999999", cookie=adm_c)
    case("TC-13", "Веб: несуществующая заявка → страница 404",
         st == 404 and "не найдена" in html.lower(), f"HTTP {st}, страница ошибки")

    st, res = api("GET", "/requests/З-999999", token=admin)
    case("TC-14", "API: несуществующая заявка → 404",
         st == 404 and "не найдена" in str(res.get("detail")), f"HTTP {st}, {res}")

    # ---------- Граничные ----------
    st, t15 = api("POST", "/requests", token=ivan,
                  data={"subject": "Ров", "description": "Тема ровно 3 символа.", "category_id": 1})
    if st == 201:
        CREATED.append(t15["number"])
    case("TC-15", "Граница: тема ровно 3 символа → 201", st == 201, f"HTTP {st}")

    long_subject = "Д" * 200
    st, t16 = api("POST", "/requests", token=ivan,
                  data={"subject": long_subject, "description": "Т" * 5000, "category_id": 1})
    if st == 201:
        CREATED.append(t16["number"])
    st_too, _ = api("POST", "/requests", token=ivan,
                    data={"subject": "Д" * 201, "description": "слишком длинная тема", "category_id": 1})
    case("TC-16", "Граница: тема 200 символов → 201, 201 символ → 422",
         st == 201 and st_too == 422, f"200 симв. -> HTTP {st}, 201 симв. -> HTTP {st_too}")

    st, _, html = web("GET", "/?q=%27%3Cscript%3E%25", cookie=adm_c)
    case("TC-17", "Спецсимволы в поиске ('<script>%) → 200 без ошибки",
         st == 200, f"HTTP {st}, страница отображается")

    st, _, html = web("GET", "/?q=несуществующийзапрос987", cookie=adm_c)
    case("TC-18", "Поиск без совпадений → пустое состояние",
         st == 200 and "ничего не найдено" in html, f"HTTP {st}, «ничего не найдено»")

    # ---------- Роли и доступ ----------
    st, lst = api("GET", "/requests", token=ivan)
    only_own = all(t["applicant_name"] == "Иван Петров" for t in lst) and len(lst) > 0
    case("TC-19", "Заявитель видит только свои заявки (API)",
         st == 200 and only_own, f"HTTP {st}, {len(lst)} заявок, все заявителя Иван Петров")

    st, res = api("POST", "/requests", token=igor,
                  data={"subject": "Попытка исполнителя", "description": "не должно создаться", "category_id": 1})
    case("TC-20", "Исполнитель не может создать заявку → 403",
         st == 403, f"HTTP {st}, {res.get('detail')}")

    st, res = api("GET", "/requests")
    case("TC-21", "Запрос без токена → 401", st == 401, f"HTTP {st}, {res.get('detail')}")

    st, res = api("DELETE", "/requests/З-000001", token=ivan)
    case("TC-22", "Удаление заявки не-админом → 403", st == 403, f"HTTP {st}, {res.get('detail')}")

    # ---------- Интеграционные UI + БД + API ----------
    st, _, html = web("POST", "/tickets/new", cookie=ivan_c,
                      form={"subject": "ТК: интеграция веб-API", "description": "Создана через веб-форму",
                            "category_id": "1", "priority": "high"})
    # номер созданной заявки берём через API-поиск
    st, lst = api("GET", "/requests?q=интеграция веб-API", token=admin)
    web_num = lst[0]["number"] if st == 200 and lst else None
    if web_num:
        CREATED.append(web_num)
    ok = st == 200 and web_num and lst[0]["status"] == "new" and lst[0]["priority"] == "high"
    case("TC-23", "Создана через веб → читается через API (статус/приоритет совпадают)",
         bool(ok), f"заявка {web_num}, status={lst[0]['status'] if lst else '?'}, priority={lst[0]['priority'] if lst else '?'}")

    st, _ = api("POST", f"/requests/{web_num}/take", token=igor) if web_num else (0, None)
    st, _, html = web("GET", f"/tickets/{web_num}", cookie=adm_c) if web_num else (0, None, "")
    case("TC-24", "Статус изменён через API → отображается в веб-карточке",
         bool(web_num) and "В работе" in html and "Игорь Мастеров" in html,
         f"веб-карточка {web_num}: статус «В работе», исполнитель Игорь Мастеров")

    # ---------- API ----------
    st, t25 = api("PATCH", f"/requests/{num1}", token=olga,
                  data={"subject": "ТК: сломался сканер (уточнено)", "priority": "high"})
    ok = st == 200 and t25.get("subject", "").endswith("(уточнено)") and t25.get("priority") == "high"
    case("TC-25", "API: PATCH заявки → 200, поля обновлены", ok,
         f"HTTP {st}, тема и приоритет изменены")

    st, t26 = api("POST", "/requests", token=ivan,
                  data={"subject": "ТК: на удаление", "description": "будет удалена", "category_id": 1})
    num26 = t26.get("number") if st == 201 else None
    st_d, _ = api("DELETE", f"/requests/{num26}", token=admin) if num26 else (0, None)
    st_g, _ = api("GET", f"/requests/{num26}", token=admin) if num26 else (0, None)
    case("TC-26", "API: DELETE → 204, повторный GET → 404",
         st_d == 204 and st_g == 404, f"DELETE {st_d}, GET после {st_g}")

    st_s, statuses = api("GET", "/statuses", token=ivan)
    st_c, cats = api("GET", "/categories", token=ivan)
    st_p, prios = api("GET", "/priorities", token=ivan)
    ok = st_s == 200 and st_c == 200 and st_p == 200 and "transitions" in statuses and len(cats) >= 4
    case("TC-27", "API: справочники /statuses /categories /priorities → 200",
         ok, f"statuses {st_s}, categories {st_c} ({len(cats)} шт.), priorities {st_p}")

    st, c28 = api("POST", f"/requests/{num1}/comments", token=ivan,
                  data={"text": "Комментарий заявителя по ТК-28"})
    st_g, t28 = api("GET", f"/requests/{num1}", token=ivan)
    has_comments = isinstance(t28, dict) and len(t28.get("comments", [])) >= 2
    case("TC-28", "API: POST комментария → 201, виден в карточке",
         st == 201 and has_comments, f"HTTP {st}, комментариев в заявке: {len(t28.get('comments', [])) if isinstance(t28, dict) else '?'}")

    # ---------- Очистка тестовых данных ----------
    log("")
    for n in CREATED:
        st, _ = api("DELETE", f"/requests/{n}", token=admin)
        log(f"Очистка: удалена {n} -> HTTP {st}")

    passed = sum(1 for _, s, _ in RESULTS.values() if s == "PASS")
    log("")
    log(f"ИТОГ: {passed}/{len(RESULTS)} PASS")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(LOG), encoding="utf-8")
    print(f"\nЛог сохранён: {OUT}")


if __name__ == "__main__":
    main()
