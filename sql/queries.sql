-- =============================================================
-- queries.sql — демонстрационные SQL-запросы (лаба №5)
-- Выполняется после schema.sql + seed.sql.
-- Содержит: 5 INSERT, 5 SELECT (3 с WHERE, 2 с JOIN),
--           2 UPDATE, 2 DELETE.
-- Результаты SELECT зафиксированы в docs/sql_results.txt.
-- =============================================================

-- ---------- INSERT (5) ----------

-- INSERT 1: новый пользователь-исполнитель
INSERT INTO users (id, username, password_hash, full_name, role_id)
VALUES (6, 'petr', '$2b$12$demoHASHpetr00000000000000000000000000000000000000', 'Пётр Ремонтников', 3);

-- INSERT 2: новая категория
INSERT INTO categories (id, name) VALUES (6, 'Бухгалтерия');

-- INSERT 3: новая заявка от Марии
INSERT INTO requests (id, number, subject, description, category_id, status_id, applicant_id)
VALUES (6, 'З-000006', 'Справка о доходах', 'Нужна справка 2-НДФЛ за 2025 год.', 6, 1, 5);

-- INSERT 4: комментарий оператора к новой заявке
INSERT INTO comments (request_id, author_id, text)
VALUES (6, 2, 'Принято в работу, уточняю у бухгалтерии.');

-- INSERT 5: комментарий заявителя
INSERT INTO comments (request_id, author_id, text)
VALUES (5, 4, 'Дополнение: ПК в переговорной №2, серийный номер SN-5521.');

-- ---------- UPDATE (2) ----------

-- UPDATE 1: заявка З-000002 закрыта после выполнения
UPDATE requests
SET status_id = 4
WHERE number = 'З-000002';

-- UPDATE 2: заявке З-000005 назначен исполнитель Пётр
UPDATE requests
SET executor_id = 6
WHERE number = 'З-000005';

-- ---------- SELECT (5) ----------

-- SELECT 1 (WHERE): все новые заявки
SELECT r.number, r.subject, s.name AS status
FROM requests r
JOIN statuses s ON s.id = r.status_id
WHERE s.code = 'new';

-- SELECT 2 (WHERE): заявки категории «ИТ-оборудование»
SELECT r.number, r.subject
FROM requests r
JOIN categories c ON c.id = r.category_id
WHERE c.name = 'ИТ-оборудование';

-- SELECT 3 (WHERE): комментарии к заявке З-000001
SELECT c.text, c.created_at
FROM comments c
JOIN requests r ON r.id = c.request_id
WHERE r.number = 'З-000001';

-- SELECT 4 (JOIN): заявки с ФИО заявителя, исполнителя и статусом
SELECT r.number,
       r.subject,
       u1.full_name AS applicant,
       u2.full_name AS executor,
       s.name AS status
FROM requests r
JOIN users u1    ON u1.id = r.applicant_id
LEFT JOIN users u2 ON u2.id = r.executor_id
JOIN statuses s  ON s.id = r.status_id
ORDER BY r.created_at DESC;

-- SELECT 5 (JOIN + WHERE + группировка): сколько заявок у каждого исполнителя в работе
SELECT u.full_name AS executor, COUNT(*) AS in_work_count
FROM requests r
JOIN users u    ON u.id = r.executor_id
JOIN statuses s ON s.id = r.status_id
WHERE s.code = 'in_work'
GROUP BY u.full_name;

-- ---------- DELETE (2) ----------

-- DELETE 1: удалить комментарий с id=4 (ошибочный)
DELETE FROM comments WHERE id = 4;

-- DELETE 2: удалить отменённую заявку З-000004 (и проверить)
DELETE FROM requests WHERE number = 'З-000004';

-- Проверка после DELETE: заявки З-000004 больше нет
SELECT COUNT(*) AS remains FROM requests WHERE number = 'З-000004';
