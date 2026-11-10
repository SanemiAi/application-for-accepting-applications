# Деплой приложения

## Запись о выполненном деплое

| Параметр | Значение |
|---|---|
| Среда развёртывания | Своя машина (Windows 10/11, Docker Desktop) |
| Способ доступа | По IP-адресу в локальной сети |
| Адрес приложения | http://192.168.1.101:8000 |
| Проверка работоспособности | http://192.168.1.101:8000/health → `{"status": "ok"}` |
| Дата деплоя | 10.11.2026 |
| Контейнеры | `ticket_system-app-1` (FastAPI), `ticket_system-db-1` (PostgreSQL 16) |

> IP-адрес выдан роутером по DHCP и может измениться после перезагрузки
> роутера/ПК. Актуальный адрес смотрите командой `ipconfig` (адаптер
> «Беспроводная сеть» / «Ethernet», строка «IPv4-адрес»).

## Почему «своя машина»

Удалённые среды (Яндекс.Облако, TimeWeb) требуют платного аккаунта и настройки
доступа. Для учебного проекта выбран вариант «своя машина»: приложение собрано
в Docker-образ, запущено локально и доступно другим устройствам в локальной сети
по IP-адресу — этого достаточно, чтобы преподаватель или одногруппники открыли
его из браузера.

## Полная инструкция повторного деплоя с нуля

Выполняется на любой машине с установленным Docker Desktop.

### 1. Получить код

```bash
git clone https://github.com/SanemiAi/application-for-accepting-applications.git
cd application-for-accepting-applications
git checkout main
```

### 2. Настроить окружение

```bash
cp .env.example .env
```

Открыть `.env` и при необходимости изменить значения
(порт `APP_PORT`, пароли БД, `JWT_SECRET`, пароль стартового админа).
Для учебного запуска можно оставить всё как есть.

### 3. Собрать и запустить

```bash
docker compose up --build -d
```

Docker Compose автоматически подхватывает `.env` из папки проекта.
При первом запуске создаются таблицы, стартовый администратор и категории.

### 4. Проверить, что приложение живо

```bash
curl http://localhost:8000/health        # {"status": "ok"}
```

Веб-интерфейс: http://localhost:8000 (вход `admin` / `admin123`).

### 5. (Опционально) Наполнить демонстрационными данными

```bash
docker compose exec app python tools/seed_demo.py
```

6 пользователей, 5 категорий, 12 заявок в разных статусах.
Скрипт идемпотентен — повторный запуск не создаёт дубликатов.

### 6. Открыть доступ из локальной сети

1. Узнать IP машины: `ipconfig` → строка «IPv4-адрес» (например, `192.168.1.101`).
2. Разрешить входящие на порт в брандмауэре Windows
   (PowerShell **от имени администратора**):

   ```powershell
   netsh advfirewall firewall add rule name="TicketSystem 8000" dir=in action=allow protocol=TCP localport=8000
   ```

3. С другого устройства в той же сети открыть `http://<IP>:8000`.

Удалить правило после показа:

```powershell
netsh advfirewall firewall delete rule name="TicketSystem 8000"
```

### 7. Остановка и обновление

```bash
docker compose down          # остановить (данные БД сохранятся)
docker compose down -v       # остановить и удалить данные БД

git pull                     # обновление кода
docker compose up --build -d # пересборка и перезапуск
```

## Требования к машине

- Docker Desktop (Windows/Mac) или Docker Engine + Compose plugin (Linux);
- свободные порты `8000` (приложение) и `5432` (PostgreSQL) — меняются в `.env`;
- ~500 МБ на образы (`python:3.12-slim`, `postgres:16`).

## Проверка после деплоя

| Проверка | Команда | Ожидается |
|---|---|---|
| Приложение живо | `curl http://localhost:8000/health` | `{"status": "ok"}` |
| Веб-интерфейс | браузер → http://localhost:8000 | страница входа |
| API | `curl http://localhost:8000/api/statuses` (с токеном) | список статусов |
| База работает | `docker compose exec db pg_isready -U postgres` | `accepting connections` |
| Сквозные тесты | `python tests/e2e_check.py` | `41 passed, 0 failed` |
