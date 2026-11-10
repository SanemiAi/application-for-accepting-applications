# -*- coding: utf-8 -*-
"""Наполнение рабочей БД демонстрационными данными (ЛР №6, п. 8):
4 пользователя ролей, 5 категорий, 12 заявок в разных статусах с комментариями.

Запуск из контейнера приложения:
    docker compose exec app python tools/seed_demo.py
Идемпотентно: повторный запуск не создаёт дубликатов.
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.credentials import required      # noqa: E402
from app.auth import hash_password          # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app import models                      # noqa: E402

# Пароли не хранятся в репозитории: admin — из ADMIN_PASSWORD,
# демо-пользователи — единый пароль из SEED_DEMO_PASSWORD
# (если не задан, генерируется случайный и печатается в консоль).
USERS = [
    ("admin", "Администратор системы", models.Role.ADMIN),
    ("olga", "Ольга Сидорова", models.Role.OPERATOR),
    ("igor", "Игорь Мастеров", models.Role.EXECUTOR),
    ("petr", "Пётр Ремонтников", models.Role.EXECUTOR),
    ("ivan", "Иван Петров", models.Role.APPLICANT),
    ("maria", "Мария Кузнецова", models.Role.APPLICANT),
]

CATEGORIES = [
    "Техподдержка", "Снабжение", "Административный вопрос",
    "Кадровый вопрос", "ИТ-оборудование",
]

# (тема, описание, категория, статус, приоритет, заявитель, исполнитель, комментарии)
S = models.Status
P = models.Priority
TICKETS = [
    ("Не работает принтер HP LaserJet", "Принтер в бухгалтерии не печатает, горит красный индикатор.",
     "Техподдержка", S.CLOSED, P.HIGH, "ivan", "igor",
     [("olga", "Передала исполнителю, приоритет высокий."),
      ("igor", "Заменён картридж и ролик подачи. Печать восстановлена."),
      ("ivan", "Проверил — всё работает, спасибо!")]),
    ("Закупить бумагу А4", "В отделе заканчивается бумага, нужно 10 пачек.",
     "Снабжение", S.CLOSED, P.MEDIUM, "maria", "igor",
     [("igor", "Заказ оформлен, бумага доставлена на склад.")]),
    ("Оформить пропуск новому сотруднику", "Нужен пропуск с 01.11, данные выслал в комментарии.",
     "Административный вопрос", S.DONE, P.MEDIUM, "ivan", "petr",
     [("ivan", "ФИО: Смирнов Алексей, отдел продаж."),
      ("petr", "Пропуск оформлен, можно забрать в охране.")]),
    ("Вопрос по остатку отпуска", "Уточните, сколько дней отпуска осталось на текущий год.",
     "Кадровый вопрос", S.IN_WORK, P.LOW, "maria", "igor",
     [("olga", "Запросила данные в отделе кадров.")]),
    ("Заменить системный блок в переговорной", "Старый ПК в переговорной №2 не загружается, SN-5521.",
     "ИТ-оборудование", S.NEW, P.MEDIUM, "ivan", None, []),
    ("Не приходят письма на корпоративную почту", "С утра пустой ящик, отправители получают отказ.",
     "Техподдержка", S.IN_WORK, P.HIGH, "maria", "igor",
     [("igor", "Проверяю логи почтового сервера.")]),
    ("Справка 2-НДФЛ за 2025 год", "Нужна справка для банка, желательно до пятницы.",
     "Кадровый вопрос", S.NEW, P.MEDIUM, "ivan", None, []),
    ("Закупить картриджи для МФУ", "МФУ Kyocera на 3 этаже, картридж TK-1150 — 2 шт.",
     "Снабжение", S.NEW, P.LOW, "maria", None, []),
    ("Не работает кондиционер в серверной", "Температура 29°C и растёт, требуется срочный выезд.",
     "ИТ-оборудование", S.IN_WORK, P.HIGH, "ivan", "petr",
     [("olga", "Согласовала выезд сервисной службы на сегодня."),
      ("petr", "Диагностика: забит фильтр, чистка выполнена.")]),
    ("Обновить антивирус на рабочих местах", "В отделе маркетинга базы антивируса старше 30 дней.",
     "Техподдержка", S.NEW, P.MEDIUM, "maria", None, []),
    ("Заявка на канцелярию", "Нужны: ручки (50), папки (20), маркеры (10).",
     "Снабжение", S.DONE, P.LOW, "ivan", "igor",
     [("igor", "Выдано со склада, расписка получена.")]),
    ("Доступ к 1С для нового бухгалтера", "Создать учётную запись и выдать права чтения.",
     "Административный вопрос", S.NEW, P.HIGH, "maria", None, []),
]


def main():
    Base.metadata.create_all(bind=engine)
    demo_password = os.environ.get("SEED_DEMO_PASSWORD")
    if not demo_password:
        demo_password = secrets.token_urlsafe(9)
        print(f"SEED_DEMO_PASSWORD не задан, сгенерирован пароль демо-пользователей: {demo_password}")
    admin_password = required("ADMIN_PASSWORD")
    db = SessionLocal()
    try:
        users = {}
        for username, full_name, role in USERS:
            password = admin_password if role == models.Role.ADMIN else demo_password
            u = db.query(models.User).filter_by(username=username).first()
            if not u:
                u = models.User(username=username, password_hash=hash_password(password),
                                full_name=full_name, role=role)
                db.add(u)
                db.flush()
            else:
                u.password_hash = hash_password(password)
            users[username] = u

        cats = {}
        for name in CATEGORIES:
            c = db.query(models.Category).filter_by(name=name).first()
            if not c:
                c = models.Category(name=name)
                db.add(c)
                db.flush()
            cats[name] = c

        created = 0
        for subject, description, cat, status, prio, applicant, executor, comments in TICKETS:
            if db.query(models.Ticket).filter_by(subject=subject).first():
                continue
            t = models.Ticket(
                number="tmp", subject=subject, description=description,
                category_id=cats[cat].id, status=status, priority=prio,
                applicant_id=users[applicant].id,
                executor_id=users[executor].id if executor else None,
            )
            db.add(t)
            db.flush()
            t.number = f"З-{t.id:06d}"
            for author, text in comments:
                db.add(models.Comment(ticket_id=t.id, author_id=users[author].id, text=text))
            created += 1

        db.commit()
        total = db.query(models.Ticket).count()
        print(f"Добавлено заявок: {created}. Всего в БД: {total}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
