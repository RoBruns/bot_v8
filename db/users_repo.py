from typing import List, Optional
from db.database import get_connection


def add_user(username: str, password: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO v8_users (username, password) VALUES (?, ?)",
        (username, password)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def remove_user(user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM v8_users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def list_users() -> List[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, username, active FROM v8_users ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_credentials(user_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute(
        "SELECT username, password FROM v8_users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
