"""Tiny SQLite layer for users and recommendation history."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config


@contextmanager
def get_conn():
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                category TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, id DESC);
            """
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_user(username: str, email: str, password_hash: str) -> int:
    """Raises sqlite3.IntegrityError if the username already exists."""
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?,?,?,?)",
            (username, email, password_hash, _now()),
        )
        return cur.lastrowid


def get_user_by_username(username: str):
    with get_conn() as c:
        row = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int):
    with get_conn() as c:
        row = c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def save_history(user_id: int, category: str, request: dict, response: dict) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO history (user_id, category, request_json, response_json, created_at) VALUES (?,?,?,?,?)",
            (user_id, category, json.dumps(request), json.dumps(response), _now()),
        )
        return cur.lastrowid


def _row_to_history(row) -> dict:
    return {
        "id": row["id"],
        "category": row["category"],
        "request": json.loads(row["request_json"]),
        "response": json.loads(row["response_json"]),
        "created_at": row["created_at"],
    }


def list_history(user_id: int, limit: int = 50, category: str | None = None) -> list[dict]:
    sql = "SELECT * FROM history WHERE user_id = ?"
    args: list = [user_id]
    if category:
        sql += " AND category = ?"
        args.append(category)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with get_conn() as c:
        return [_row_to_history(r) for r in c.execute(sql, args).fetchall()]


def get_history_item(user_id: int, item_id: int):
    with get_conn() as c:
        row = c.execute(
            "SELECT * FROM history WHERE id = ? AND user_id = ?", (item_id, user_id)
        ).fetchone()
        return _row_to_history(row) if row else None


def count_history_by_category(user_id: int) -> dict:
    with get_conn() as c:
        rows = c.execute(
            "SELECT category, COUNT(*) n FROM history WHERE user_id = ? GROUP BY category",
            (user_id,),
        ).fetchall()
    return {r["category"]: r["n"] for r in rows}
