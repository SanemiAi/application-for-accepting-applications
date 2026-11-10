"""Скриншоты для отчётов лабораторных №6–8.

Снимает реально работающее приложение (нужен запущенный docker compose):
- docs/screenshots_lab6/ — экраны функционала (ЛР6)
- docs/screenshots_lab7/ — Swagger UI: успешные и ошибочные запросы (ЛР7)
- docs/screenshots_lab8/ — деплой: терминал, health и приложение по LAN-адресу (ЛР8)

Запуск: python tools/make_screenshots_lab678.py
"""
import json
import re
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.credentials import required  # noqa: E402

BASE = "http://localhost:8000"
OUT6 = ROOT / "docs" / "screenshots_lab6"
OUT7 = ROOT / "docs" / "screenshots_lab7"
OUT8 = ROOT / "docs" / "screenshots_lab8"
DOCKER = r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"

# Пароль берётся из окружения/.env, в репозитории не хранится
ADMIN = ("admin", required("ADMIN_PASSWORD"))


def lan_ip() -> str:
    """IPv4 домашней сети (192.168.x.x), fallback — hostname resolve."""
    try:
        out = subprocess.run(["ipconfig"], capture_output=True, text=True,
                             encoding="cp866", errors="replace").stdout
        ips = re.findall(r"IPv4[^:]*:\s*(\d+\.\d+\.\d+\.\d+)", out)
        for ip in ips:
            if ip.startswith("192.168."):
                return ip
    except Exception:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def login(page):
    page.goto(f"{BASE}/login")
    page.fill('input[name="username"]', ADMIN[0])
    page.fill('input[name="password"]', ADMIN[1])
    page.click('.card form button')
    page.wait_for_url(BASE + "/")


def shot(page, path: Path, full=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=full)
    print(f"  {path.relative_to(ROOT)}")


def terminal_html(title: str, text: str) -> str:
    lines = "".join(
        f'<div class="line">{l.replace("<", "&lt;")}</div>' for l in text.rstrip().splitlines()
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
body {{ background:#0c0c0c; margin:0; padding:0; font-family:Consolas,monospace; }}
.term {{ padding:18px 22px; color:#e6e6e6; font-size:15px; line-height:1.45; }}
.title {{ color:#8a8a8a; border-bottom:1px solid #333; padding:10px 22px; font-size:13px; }}
.line {{ white-space:pre-wrap; }}
.prompt {{ color:#4ec94e; }}
</style></head><body>
<div class="title">{title}</div>
<div class="term">{lines}</div>
</body></html>"""


def shot_terminal(page, title: str, text: str, path: Path):
    tmp = ROOT / "docs" / "_terminal_tmp.html"
    tmp.write_text(terminal_html(title, text), encoding="utf-8")
    page.goto(tmp.as_uri())
    page.wait_for_timeout(300)
    shot(page, path)
    tmp.unlink()


# ---------------- ЛР6: экраны функционала ----------------

def lab6(page):
    print("ЛР6: экраны приложения")
    login(page)

    page.goto(BASE + "/")
    page.wait_for_selector("table")
    shot(page, OUT6 / "01_list.png")

    page.goto(f"{BASE}/tickets/new")
    page.wait_for_selector("form")
    shot(page, OUT6 / "02_new_ticket.png")

    page.goto(f"{BASE}/tickets/З-000009")
    page.wait_for_selector("h2")
    shot(page, OUT6 / "03_ticket_detail.png", full=True)

    page.goto(f"{BASE}/tickets/З-000009/edit")
    page.wait_for_selector("form")
    shot(page, OUT6 / "04_edit_priority.png")

    page.goto(f"{BASE}/?q=Снабжение")
    page.wait_for_selector("table")
    shot(page, OUT6 / "05_search_category.png")

    page.goto(f"{BASE}/?priority=high")
    page.wait_for_selector("table")
    shot(page, OUT6 / "06_filter_priority.png")

    page.goto(f"{BASE}/tickets/new")
    page.eval_on_selector('input[name="subject"]',
                          "el => { el.removeAttribute('minlength'); el.removeAttribute('required') }")
    page.fill('input[name="subject"]', "ab")
    page.fill('textarea[name="description"]', "проверка валидации")
    page.click('.card form button')
    page.wait_for_selector(".alert", timeout=5000)
    shot(page, OUT6 / "07_validation_error.png")

    page.goto(f"{BASE}/tickets/З-999999")
    page.wait_for_selector("h2")
    shot(page, OUT6 / "08_error_404.png")

    page.goto(f"{BASE}/?q=несуществующийзапрос123")
    page.wait_for_selector("text=ничего не найдено")
    shot(page, OUT6 / "09_empty_search.png")

    # Кнопка удаления видна администратору в карточке заявки
    page.goto(f"{BASE}/tickets/З-000011")
    page.wait_for_selector("h2")
    shot(page, OUT6 / "10_delete_button.png", full=True)


# ---------------- ЛР7: Swagger UI ----------------

def swagger_authorize(page):
    page.click("button.authorize")
    page.wait_for_selector(".modal-ux-content", timeout=8000)
    page.fill('.modal-ux-content input[type="text"]', ADMIN[0])
    page.fill('.modal-ux-content input[type="password"]', ADMIN[1])
    page.click(".modal-ux-content button.authorize")
    page.wait_for_timeout(700)
    page.click(".modal-ux-content button.btn-done, .modal-ux .close-modal, .modal-ux-content button.btn-clear", timeout=5000)
    page.wait_for_timeout(400)


def swagger_execute(page, op_id: str, shot_path: Path,
                    param=None, body=None, wait_status=True):
    op = page.locator(f'[id="{op_id}"]')
    op.scroll_into_view_if_needed()
    if "is-open" not in (op.get_attribute("class") or ""):
        op.locator(".opblock-summary").click()
        page.wait_for_timeout(600)
    try:
        tryout = op.locator("button.try-out__btn")
        if tryout.count() and tryout.is_visible():
            tryout.click(timeout=3000)
            page.wait_for_timeout(500)
    except Exception:
        pass
    if param:
        inp = op.locator('input[placeholder]').first
        inp.wait_for(timeout=5000)
        inp.fill(param)
    if body:
        ta = op.locator("textarea.body-param__text")
        ta.wait_for(timeout=5000)
        ta.fill(json.dumps(body, ensure_ascii=False))
    execute = op.locator("button.execute")
    execute.wait_for(timeout=8000)
    execute.click()
    if wait_status:
        op.locator(".responses-inner .response-col_status, .live-responses-table .response-col_status").first.wait_for(timeout=15000)
    page.wait_for_timeout(900)
    op.screenshot(path=str(shot_path))
    print(f"  {shot_path.relative_to(ROOT)}")


def lab7(page, context):
    print("ЛР7: Swagger UI")
    page.goto(f"{BASE}/docs")
    page.wait_for_selector(".swagger-ui", timeout=15000)
    page.wait_for_timeout(1500)
    shot(page, OUT7 / "01_swagger_overview.png")

    page.click("button.authorize")
    page.wait_for_selector(".modal-ux-content", timeout=8000)
    page.fill('.modal-ux-content input[type="text"]', ADMIN[0])
    page.fill('.modal-ux-content input[type="password"]', ADMIN[1])
    shot(page, OUT7 / "02_swagger_authorize.png")
    page.click(".modal-ux-content button.authorize")
    page.wait_for_timeout(800)
    try:
        page.click(".modal-ux-content button.btn-done", timeout=3000)
    except Exception:
        page.click(".modal-ux .close-modal", timeout=3000)
    page.wait_for_timeout(400)

    swagger_execute(
        page,
        "operations-Заявки-list_tickets_api_requests_get",
        OUT7 / "03_get_requests_200.png",
    )

    new_number = None
    body = {"subject": "Заявка из Swagger UI", "description": "Создана для отчёта ЛР7",
            "category_id": 1, "priority": "low"}
    swagger_execute(
        page,
        "operations-Заявки-create_ticket_api_requests_post",
        OUT7 / "04_post_create_201.png",
        body=body,
    )
    st, resp = api_call("GET", "/requests?q=Swagger", ADMIN)
    if isinstance(resp, list) and resp:
        new_number = resp[0]["number"]

    swagger_execute(
        page,
        "operations-Заявки-get_ticket_api_requests__number__get",
        OUT7 / "05_get_one_404.png",
        param="З-999999",
    )

    swagger_execute(
        page,
        "operations-Заявки-create_ticket_api_requests_post",
        OUT7 / "06_post_invalid_422.png",
        body={"subject": "ab", "description": "", "category_id": 1},
    )

    swagger_execute(
        page,
        "operations-Справочники-list_statuses_api_statuses_get",
        OUT7 / "07_get_statuses_200.png",
    )

    if new_number:
        swagger_execute(
            page,
            "operations-Заявки-delete_ticket_api_requests__number__delete",
            OUT7 / "08_delete_204.png",
            param=new_number,
        )


def api_call(method: str, path: str, creds):
    req = urllib.request.Request(
        f"{BASE}/api/auth/login",
        data=f"username={creds[0]}&password={creds[1]}".encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    token = json.loads(urllib.request.urlopen(req).read())["access_token"]
    req = urllib.request.Request(
        f"{BASE}/api{path}", method=method,
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ---------------- ЛР8: деплой ----------------

def lab8(page, ip: str):
    print("ЛР8: деплой")
    ps = subprocess.run(
        [DOCKER, "ps", "--format",
         "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    logs = subprocess.run(
        [DOCKER, "compose", "logs", "--tail=6", "app"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    ).stdout
    shot_terminal(
        page, "PowerShell — docker ps",
        "PS C:\\Users\\Maxim\\Desktop\\ticket_system> docker ps\n" + ps.strip(),
        OUT8 / "01_docker_ps.png",
    )
    shot_terminal(
        page, "PowerShell — docker compose",
        "PS C:\\Users\\Maxim\\Desktop\\ticket_system> docker compose logs --tail=6 app\n" + logs.strip(),
        OUT8 / "02_compose_logs.png",
    )

    lan = f"http://{ip}:8000"
    page.goto(f"{lan}/health")
    page.wait_for_timeout(700)
    shot(page, OUT8 / "03_health_lan.png")

    page.goto(f"{lan}/login")
    page.wait_for_selector("form")
    shot(page, OUT8 / "04_app_lan.png")

    page.goto(f"{lan}/docs")
    page.wait_for_selector(".swagger-ui", timeout=15000)
    page.wait_for_timeout(1200)
    shot(page, OUT8 / "05_swagger_lan.png")

    health = urllib.request.urlopen(f"{lan}/health").read().decode()
    st, statuses = api_call("GET", "/statuses", ADMIN)
    curl_text = (
        f"PS> curl http://{ip}:8000/health\n{health}\n\n"
        f"PS> # GET /api/statuses на удалённый адрес (с JWT-токеном)\n"
        f"PS> curl -H \"Authorization: Bearer <token>\" http://{ip}:8000/api/statuses\n"
        f"HTTP {st}\n" + json.dumps(statuses, ensure_ascii=False, indent=2)[:900]
    )
    shot_terminal(page, f"Обращение к приложению по адресу {lan}", curl_text,
                  OUT8 / "06_api_lan_curl.png")


def main():
    ip = lan_ip()
    print(f"LAN IP: {ip}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        lab6(page)
        lab7(page, context)
        lab8(page, ip)
        browser.close()
    print("Готово.")


if __name__ == "__main__":
    main()
