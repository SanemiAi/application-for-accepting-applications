# -*- coding: utf-8 -*-
"""Делает скриншоты экранов веб-интерфейса для отчёта по лабе №4.
Приложение должно быть запущено (docker compose up -d)."""
import os
import sys

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "screenshots")
BASE = "http://localhost:8000"

os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 800})

    def shot(name):
        page.screenshot(path=os.path.join(OUT, name), full_page=True)
        print("OK:", name)

    # 1. Экран входа
    page.goto(BASE + "/login")
    page.wait_for_load_state("networkidle")
    shot("01_login.png")

    # Логин под администратором
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin123")
    page.click('button[type="submit"], button:has-text("Войти")')
    page.wait_for_url(BASE + "/")

    # 2. Список заявок с фильтрами
    shot("02_tickets_list.png")

    # 3. Форма создания заявки
    page.goto(BASE + "/tickets/new")
    shot("03_new_ticket.png")

    # 4. Карточка заявки (первая из списка)
    page.goto(BASE + "/")
    link = page.locator("table a").first
    if link.count():
        link.click()
        page.wait_for_load_state("networkidle")
        shot("04_ticket_detail.png")

        # 5. Экран редактирования
        page.goto(page.url.rstrip("/") + "/edit")
        shot("05_ticket_edit.png")

    # 6. Список с применённым фильтром по статусу
    page.goto(BASE + "/?status=new")
    shot("06_filter_status.png")

    browser.close()
print("Скриншоты сохранены в docs/screenshots/")
