# -*- coding: utf-8 -*-
"""Собирает database/tickets.db из sql/schema.sql + sql/seed.sql,
выполняет sql/queries.sql и сохраняет результаты SELECT в docs/sql_results.txt."""
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "database", "tickets.db")
OUT_PATH = os.path.join(ROOT, "docs", "sql_results.txt")


def read(name):
    with open(os.path.join(ROOT, "sql", name), encoding="utf-8") as f:
        return f.read()


def split_statements(sql):
    parts, buf = [], []
    for line in sql.splitlines():
        buf.append(line)
        if line.rstrip().endswith(";"):
            parts.append("\n".join(buf))
            buf = []
    if buf:
        parts.append("\n".join(buf))
    return [p for p in (p.strip() for p in parts) if p and p != ";"]


def strip_comments(stmt):
    return "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(read("schema.sql"))
    conn.executescript(read("seed.sql"))
    conn.commit()

    out = ["Результаты выполнения sql/queries.sql на database/tickets.db", "=" * 70, ""]
    for stmt in split_statements(read("queries.sql")):
        code = strip_comments(stmt)
        if not code:
            continue
        comments = [l.strip()[2:].strip() for l in stmt.splitlines() if l.strip().startswith("--")]
        title = next((c for c in reversed(comments) if not set(c) <= set("=- ")), "(запрос)")
        cur = conn.execute(code)
        if code.upper().startswith("SELECT"):
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            out.append(f"### {title}")
            out.append(" | ".join(cols))
            out.append("-" * 60)
            for r in rows:
                out.append(" | ".join(str(v) for v in r))
            out.append(f"({len(rows)} строк)\n")
        else:
            conn.commit()
            out.append(f"### {title}")
            out.append(f"OK, затронуто строк: {cur.rowcount}\n")
    conn.close()

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"OK: {os.path.relpath(DB_PATH, ROOT)} и {os.path.relpath(OUT_PATH, ROOT)} созданы")


if __name__ == "__main__":
    main()
