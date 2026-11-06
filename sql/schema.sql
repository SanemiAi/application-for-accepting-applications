-- =============================================================
-- schema.sql — создание структуры БД «Система учёта заявок»
-- Диалект: SQLite (совместимо с PostgreSQL по именам и связям).
-- Скрипт можно выполнять повторно: таблицы пересоздаются.
-- =============================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS comments;
DROP TABLE IF EXISTS requests;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS statuses;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS roles;

-- Роли пользователей (Заявитель, Оператор, Исполнитель, Администратор)
CREATE TABLE roles (
    id   INTEGER PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL
);

-- Пользователи системы
CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    username      VARCHAR(64)  NOT NULL UNIQUE,
    password_hash VARCHAR(256) NOT NULL,
    full_name     VARCHAR(128),
    role_id       INTEGER      NOT NULL REFERENCES roles(id)
);

-- Статусы заявок (Новая, В работе, Выполнена, Закрыта)
CREATE TABLE statuses (
    id         INTEGER PRIMARY KEY,
    code       VARCHAR(20) NOT NULL UNIQUE,
    name       VARCHAR(50) NOT NULL,
    sort_order INTEGER     NOT NULL
);

-- Категории заявок (не менее 4 по ТЗ)
CREATE TABLE categories (
    id   INTEGER PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE
);

-- Заявки
CREATE TABLE requests (
    id           INTEGER PRIMARY KEY,
    number       VARCHAR(20)  NOT NULL UNIQUE,   -- З-000001
    subject      VARCHAR(200) NOT NULL,
    description  TEXT         NOT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    category_id  INTEGER      REFERENCES categories(id),
    status_id    INTEGER      NOT NULL REFERENCES statuses(id),
    executor_id  INTEGER      REFERENCES users(id),   -- может быть не назначен
    applicant_id INTEGER      NOT NULL REFERENCES users(id)
);

-- Комментарии к заявкам
CREATE TABLE comments (
    id         INTEGER PRIMARY KEY,
    request_id INTEGER  NOT NULL REFERENCES requests(id),
    author_id  INTEGER  NOT NULL REFERENCES users(id),
    text       TEXT     NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для поиска по номеру и логину
CREATE INDEX idx_requests_number ON requests(number);
CREATE INDEX idx_users_username ON users(username);
