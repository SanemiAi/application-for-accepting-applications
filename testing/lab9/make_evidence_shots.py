"""Скриншоты-доказательства для тест-кейсов ЛР №9 (веб-сценарии).

Запуск: python testing/lab9/make_evidence_shots.py
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.credentials import required  # noqa: E402

BASE = "http://localhost:8000"
OUT = Path(__file__).parent / "evidence"
# Учётные данные берутся из окружения/.env, в репозитории не хранятся
ADMIN_PASSWORD = required("ADMIN_PASSWORD")
DEMO_PASSWORD = required("SEED_DEMO_PASSWORD")


def shot(page, name, full=False):
    OUT.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(OUT / name), full_page=full)
    print(f"  {name}")


def login(page, username, password):
    page.goto(f"{BASE}/login")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click(".card form button")
    page.wait_for_url(BASE + "/")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()

        login(page, "admin", ADMIN_PASSWORD)
        page.goto(BASE + "/")
        page.wait_for_selector("table")
        shot(page, "tc02_list.png")

        page.goto(f"{BASE}/?q=Снабжение")
        page.wait_for_selector("table")
        shot(page, "tc05_search_category.png")

        page.goto(f"{BASE}/tickets/new")
        page.eval_on_selector('input[name="subject"]',
                              "el => { el.removeAttribute('minlength'); el.removeAttribute('required') }")
        page.fill('input[name="subject"]', "ab")
        page.fill('textarea[name="description"]', "проверка")
        page.click(".card form button")
        page.wait_for_selector(".alert")
        shot(page, "tc10_validation_banner.png")

        page.goto(f"{BASE}/tickets/З-999999")
        page.wait_for_selector("h2")
        shot(page, "tc13_error_404.png")

        page.goto(f"{BASE}/?q=несуществующийзапрос987")
        page.wait_for_selector("text=ничего не найдено")
        shot(page, "tc18_empty_search.png")

        page.goto(f"{BASE}/logout")
        login(page, "ivan", DEMO_PASSWORD)
        page.wait_for_selector("table")
        shot(page, "tc19_applicant_own_list.png")

        browser.close()
    print("Готово.")


if __name__ == "__main__":
    main()
