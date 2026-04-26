import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS v8_users (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            active  INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS bases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            tabela_id TEXT NOT NULL,
            tabela_nome TEXT NOT NULL,
            total_cpfs INTEGER NOT NULL DEFAULT 0,
            processed INTEGER NOT NULL DEFAULT 0,
            com_saldo INTEGER NOT NULL DEFAULT 0,
            sem_saldo INTEGER NOT NULL DEFAULT 0,
            nao_autorizado INTEGER NOT NULL DEFAULT 0,
            cpf_invalido INTEGER NOT NULL DEFAULT 0,
            falha_consulta INTEGER NOT NULL DEFAULT 0,
            uploaded_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            base_name   TEXT NOT NULL,
            tabela_simulacao TEXT NOT NULL,
            started_at  TEXT NOT NULL,
            finished_at TEXT,
            total_cpfs  INTEGER NOT NULL DEFAULT 0,
            processed   INTEGER NOT NULL DEFAULT 0,
            com_saldo   INTEGER NOT NULL DEFAULT 0,
            sem_saldo   INTEGER NOT NULL DEFAULT 0,
            nao_autorizado INTEGER NOT NULL DEFAULT 0,
            cpf_invalido   INTEGER NOT NULL DEFAULT 0,
            falha_consulta INTEGER NOT NULL DEFAULT 0,
            status      TEXT NOT NULL DEFAULT 'running'
        );

        CREATE TABLE IF NOT EXISTS session_results (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            base_id    INTEGER NOT NULL REFERENCES bases(id),
            cpf        TEXT NOT NULL,
            valor      TEXT NOT NULL,
            motivo     TEXT,
            consulted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS exports (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            base_id    INTEGER NOT NULL REFERENCES bases(id),
            filename   TEXT NOT NULL,
            filepath   TEXT NOT NULL,
            exported_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS app_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        INSERT OR IGNORE INTO app_settings (key, value) VALUES ('onboarding_done', '0');
    """)
    conn.commit()
    conn.close()


def get_setting(key: str) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_setting(key: str, value: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
