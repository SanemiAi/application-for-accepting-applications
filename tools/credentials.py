# -*- coding: utf-8 -*-
"""Доступ к учётным данным для скриптов проекта (сид, e2e-проверки).

Пароли в репозитории не хранятся: значения берутся из переменных окружения,
при их отсутствии — из файла .env в корне проекта (см. .env.example).
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_dotenv():
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def required(name):
    """Вернуть значение переменной окружения или завершиться с подсказкой."""
    value = os.environ.get(name)
    if not value:
        raise SystemExit(
            f"Переменная {name} не задана. Укажите её в файле .env "
            f"в корне проекта (шаблон — .env.example) или в окружении."
        )
    return value
