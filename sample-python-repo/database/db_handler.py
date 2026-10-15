import sqlite3
import os
from pathlib import Path
from typing import Optional
from werkzeug.security import generate_password_hash


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / 'users.db'


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(os.environ.get('DATABASE_PATH') or str(DEFAULT_DATABASE_PATH))


def initialize_database() -> None:
    conn = get_connection()
    try:
        conn.execute('BEGIN')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                password_hash TEXT
            )
        ''')
        columns = {row[1] for row in conn.execute('PRAGMA table_info(users)')}
        # Upgrade databases created by the original setup script.
        if 'password' in columns and 'password_hash' not in columns:
            users = conn.execute('SELECT id, password FROM users').fetchall()
            conn.execute('ALTER TABLE users RENAME COLUMN password TO password_hash')
            conn.executemany(
                'UPDATE users SET password_hash = ? WHERE id = ?',
                [(generate_password_hash(password), user_id) for user_id, password in users],
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def execute_query(query: str, params: tuple = ()) -> list:
    # FIXED: Always uses parameterized queries, consistent return type
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise  # FIXED: Re-raise instead of swallowing or returning string
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[tuple]:
    # FIXED: Parameterized, consistent return — tuple or None only
    result = execute_query("SELECT * FROM users WHERE id = ?", (user_id,))
    return result[0] if result else None
