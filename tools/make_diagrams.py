# -*- coding: utf-8 -*-
"""Генерация диаграмм проекта (Use Case, архитектура, компоненты, ER) в PNG."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def new_ax(w=12, h=8):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def actor(ax, x, y, name):
    ax.add_patch(plt.Circle((x, y + 6), 2.2, fill=False, lw=1.6))
    ax.plot([x, x], [y + 3.8, y - 2], lw=1.6, color="black")
    ax.plot([x - 2.6, x + 2.6], [y + 1.6, y + 1.6], lw=1.6, color="black")
    ax.plot([x, x - 2.2], [y - 2, y - 5], lw=1.6, color="black")
    ax.plot([x, x + 2.2], [y - 2, y - 5], lw=1.6, color="black")
    ax.text(x, y - 8.5, name, ha="center", fontsize=10, weight="bold")


def usecase(ax, x, y, text, w=17, h=5.4):
    ax.add_patch(Ellipse((x, y), w * 2, h * 2, facecolor="#dbeafe", edgecolor="#1d4ed8", lw=1.4))
    ax.text(x, y, text, ha="center", va="center", fontsize=9.5)


def link(ax, x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color="#475569", lw=1.1, zorder=0)


def box(ax, x, y, w, h, text, fc="#f1f5f9", ec="#334155", fs=10, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.6",
                                facecolor=fc, edgecolor=ec, lw=1.5))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, weight=weight)


def arrow(ax, x1, y1, x2, y2, label=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=16, color="#334155", lw=1.5))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.5, label, ha="center", fontsize=8.5, color="#475569")


# ---------------- 1. Use Case ----------------
fig, ax = new_ax()
ax.text(50, 97, "Диаграмма вариантов использования «Система учёта заявок»",
        ha="center", fontsize=13, weight="bold")
ax.add_patch(Rectangle((18, 4), 66, 88, fill=False, edgecolor="#94a3b8", lw=1.3))
ax.text(51, 88.5, "Система учёта заявок", ha="center", fontsize=10, style="italic", color="#475569")

actor(ax, 7, 74, "Заявитель")
actor(ax, 7, 46, "Оператор")
actor(ax, 7, 20, "Исполнитель")
actor(ax, 94, 60, "Администратор")

# левая колонка — общие сценарии
usecase(ax, 38, 80, "Подать заявку", w=14)
usecase(ax, 38, 69, "Просмотреть свои заявки\n(поиск, фильтры)", w=14)
usecase(ax, 38, 58, "Дополнить описание,\nкомментировать", w=14)
usecase(ax, 38, 45, "Уточнить категорию\nи описание", w=14)
usecase(ax, 38, 35, "Назначить исполнителя,\nсменить статус", w=14)
usecase(ax, 38, 24, "Взять в работу,\nотметить выполнение", w=14)
usecase(ax, 38, 13, "Закрыть заявку", w=14)
# правая колонка — сценарии администратора
usecase(ax, 68, 74, "Управлять пользователями\nи ролями", w=14)
usecase(ax, 68, 61, "Управлять категориями", w=14)
usecase(ax, 68, 48, "Изменять любые заявки", w=14)

for y in (80, 69, 58, 13):
    link(ax, 10, 74, 24.5, y)
for y in (45, 35, 13, 80, 69):
    link(ax, 10, 46, 24.5, y)
link(ax, 10, 20, 24.5, 24)
link(ax, 10, 20, 24.5, 58)
link(ax, 10, 20, 24.5, 13)
for y in (74, 61, 48):
    link(ax, 90.5, 60, 81, y)
link(ax, 90.5, 60, 51.5, 80)
link(ax, 90.5, 60, 51.5, 35)
link(ax, 90.5, 60, 51.5, 13)

fig.savefig(os.path.join(ROOT, "docs", "use_case.png"), dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------- 2. Архитектура (слои) ----------------
fig, ax = new_ax(11, 8)
ax.text(50, 96, "Слоистая архитектура системы", ha="center", fontsize=13, weight="bold")
box(ax, 20, 76, 60, 12, "Presentation / Controller\nFastAPI routers: web_router (HTML), auth/tickets/admin (REST API)",
    fc="#dbeafe", fs=10, weight="bold")
box(ax, 20, 56, 60, 12, "Service (бизнес-правила)\nauth.py (JWT, роли), проверки доступа и переходов статусов",
    fc="#dcfce7", fs=10, weight="bold")
box(ax, 20, 36, 60, 12, "Repository / Data Access\nSQLAlchemy ORM: models.py, database.py",
    fc="#fef9c3", fs=10, weight="bold")
box(ax, 20, 16, 60, 12, "Database\nPostgreSQL 16 (users, categories, tickets, comments)",
    fc="#fee2e2", fs=10, weight="bold")
box(ax, 5, 46, 11, 22, "Шаблоны\nJinja2\n(templates/)", fc="#f1f5f9", fs=9)
arrow(ax, 50, 76, 50, 70)
arrow(ax, 50, 56, 50, 50)
arrow(ax, 50, 36, 50, 30)
arrow(ax, 20, 68, 16, 62)
ax.text(8, 63.5, "рендеринг", fontsize=8, rotation=90, color="#475569")
fig.savefig(os.path.join(ROOT, "docs", "architecture", "architecture.png"), dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------- 3. Компоненты ----------------
fig, ax = new_ax(12, 8)
ax.text(50, 96, "Диаграмма компонентов", ha="center", fontsize=13, weight="bold")
box(ax, 4, 78, 26, 12, "Браузер\n(HTML-интерфейс)", fc="#e0e7ff", weight="bold")
box(ax, 38, 78, 24, 12, "web_router\nстраницы, cookie JWT", fc="#dbeafe", weight="bold")
box(ax, 70, 78, 26, 12, "REST API routers\n/auth /tickets /admin", fc="#dbeafe", weight="bold")
box(ax, 38, 52, 24, 12, "auth.py\nJWT, хэш паролей, роли", fc="#dcfce7", weight="bold")
box(ax, 70, 52, 26, 12, "tickets_router\nбизнес-правила заявок", fc="#dcfce7", weight="bold")
box(ax, 38, 26, 24, 12, "models.py\nUser, Category, Ticket, Comment", fc="#fef9c3", weight="bold")
box(ax, 70, 26, 26, 12, "database.py\nподключение, сессии", fc="#fef9c3", weight="bold")
box(ax, 38, 4, 58, 12, "PostgreSQL 16", fc="#fee2e2", weight="bold")
box(ax, 4, 26, 26, 12, "Jinja2 templates\nbase/login/tickets/…", fc="#f1f5f9", weight="bold")
arrow(ax, 17, 78, 45, 90, "HTTP")
arrow(ax, 60, 82, 70, 82)
arrow(ax, 50, 78, 50, 66)
arrow(ax, 83, 78, 83, 66)
arrow(ax, 50, 52, 50, 40)
arrow(ax, 83, 52, 60, 40)
arrow(ax, 60, 32, 70, 32)
arrow(ax, 60, 10, 60, 24)
arrow(ax, 45, 78, 17, 40)
fig.savefig(os.path.join(ROOT, "docs", "architecture", "components.png"), dpi=150, bbox_inches="tight")
plt.close(fig)

# ---------------- 4. ER-диаграмма ----------------
fig, ax = new_ax(12, 8.5)
ax.text(50, 97, "ER-диаграмма базы данных", ha="center", fontsize=13, weight="bold")


def entity(ax, x, y, name, fields, w=30, fc="#f8fafc"):
    h = 7 + len(fields) * 4.6
    ax.add_patch(Rectangle((x, y - h), w, h, facecolor=fc, edgecolor="#334155", lw=1.4))
    ax.add_patch(Rectangle((x, y - 7), w, 7, facecolor="#bfdbfe", edgecolor="#334155", lw=1.4))
    ax.text(x + w / 2, y - 3.5, name, ha="center", va="center", fontsize=10.5, weight="bold")
    for i, f in enumerate(fields):
        ax.text(x + 1.2, y - 9.2 - i * 4.6, f, fontsize=8.6, va="center")
    return h


entity(ax, 4, 92, "users", ["PK id", "username UNIQUE NOT NULL", "password_hash NOT NULL",
                             "full_name", "role NOT NULL"])
entity(ax, 36, 92, "categories", ["PK id", "name UNIQUE NOT NULL"], fc="#f0fdf4")
entity(ax, 68, 92, "tickets", ["PK id", "number UNIQUE NOT NULL", "subject NOT NULL",
                                "description NOT NULL", "created_at NOT NULL",
                                "FK category_id → categories", "status NOT NULL",
                                "FK executor_id → users", "FK applicant_id → users"], fc="#fff7ed")
entity(ax, 36, 38, "comments", ["PK id", "FK ticket_id → tickets", "FK author_id → users",
                                "text NOT NULL", "created_at NOT NULL"], fc="#fdf4ff")

rel = [((19, 62), (68, 60), "1 : M  (заявитель)"),
       ((19, 58), (68, 54), "1 : M  (исполнитель)"),
       ((51, 92), (68, 86), "1 : M"),
       ((66, 55), (52, 38), "1 : M"),
       ((19, 54), (38, 34), "1 : M")]
for (x1, y1), (x2, y2), lab in rel:
    arrow(ax, x1, y1, x2, y2, lab)

fig.savefig(os.path.join(ROOT, "docs", "er.png"), dpi=150, bbox_inches="tight")
plt.close(fig)

print("Диаграммы сохранены: docs/use_case.png, docs/architecture/architecture.png,",
      "docs/architecture/components.png, docs/er.png")
