import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional, Any
from .config import DB_PATH
import os

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS bot_users (
                telegram_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'en',
                linked_username TEXT,
                linked_at INTEGER,
                is_admin INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS bot_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                base_url TEXT,
                admin_token TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_linked_username ON bot_users(linked_username);
            CREATE INDEX IF NOT EXISTS idx_server_name ON bot_servers(name);
        """)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

# User functions
def get_user_lang(telegram_id: int) -> str:
    with get_db() as conn:
        cur = conn.execute("SELECT language FROM bot_users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return row["language"] if row else "en"

def set_user_lang(telegram_id: int, lang: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO bot_users (telegram_id, language) VALUES (?, ?) ON CONFLICT(telegram_id) DO UPDATE SET language = ?",
            (telegram_id, lang, lang)
        )

def is_linked(telegram_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("SELECT linked_username FROM bot_users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return row and row["linked_username"] is not None

def get_linked_username(telegram_id: int) -> Optional[str]:
    with get_db() as conn:
        cur = conn.execute("SELECT linked_username FROM bot_users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return row["linked_username"] if row else None

def set_linked_username(telegram_id: int, username: str):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO bot_users (telegram_id, linked_username, linked_at) VALUES (?, ?, strftime('%s','now')) ON CONFLICT(telegram_id) DO UPDATE SET linked_username = ?, linked_at = strftime('%s','now')",
            (telegram_id, username, username)
        )

def unlink_user(telegram_id: int):
    with get_db() as conn:
        conn.execute("UPDATE bot_users SET linked_username = NULL, linked_at = NULL WHERE telegram_id = ?", (telegram_id,))

def is_admin(telegram_id: int) -> bool:
    with get_db() as conn:
        cur = conn.execute("SELECT is_admin FROM bot_users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return row and row["is_admin"] == 1

def set_admin(telegram_id: int, admin: bool):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO bot_users (telegram_id, is_admin) VALUES (?, ?) ON CONFLICT(telegram_id) DO UPDATE SET is_admin = ?",
            (telegram_id, 1 if admin else 0, 1 if admin else 0)
        )

# Server functions
def get_all_servers() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cur = conn.execute("SELECT name, base_url, admin_token FROM bot_servers ORDER BY name")
        return [dict(row) for row in cur.fetchall()]

def get_server_by_name(name: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cur = conn.execute("SELECT name, base_url, admin_token FROM bot_servers WHERE name = ?", (name,))
        row = cur.fetchone()
        return dict(row) if row else None

def add_server(name: str, base_url: str, admin_token: str) -> bool:
    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO bot_servers (name, base_url, admin_token) VALUES (?, ?, ?)",
                (name, base_url, admin_token)
            )
            return True
        except sqlite3.IntegrityError:
            return False

def remove_server(name: str) -> bool:
    with get_db() as conn:
        cur = conn.execute("DELETE FROM bot_servers WHERE name = ?", (name,))
        return cur.rowcount > 0

def get_all_linked_users() -> List[int]:
    with get_db() as conn:
        cur = conn.execute("SELECT telegram_id FROM bot_users WHERE linked_username IS NOT NULL")
        return [row["telegram_id"] for row in cur.fetchall()]