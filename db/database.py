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
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            cpf        TEXT NOT NULL,
            valor      TEXT NOT NULL,
            motivo     TEXT,
            consulted_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS exports (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id),
            filename   TEXT NOT NULL,
            filepath   TEXT NOT NULL,
            exported_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
    """)
    conn.commit()
    conn.close()
