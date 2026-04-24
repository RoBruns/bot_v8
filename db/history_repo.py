import os
from datetime import datetime, timedelta
from typing import List, Optional
from db.database import get_connection


def create_session(base_name: str, tabela_simulacao: str, total_cpfs: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO sessions (base_name, tabela_simulacao, started_at, total_cpfs)
           VALUES (?, ?, datetime('now','localtime'), ?)""",
        (base_name, tabela_simulacao, total_cpfs)
    )
    conn.commit()
    session_id = cursor.lastrowid
    conn.close()
    return session_id


def update_session_counters(session_id: int, counters: dict):
    conn = get_connection()
    conn.execute(
        """UPDATE sessions SET
            processed      = :processed,
            com_saldo      = :com_saldo,
            sem_saldo      = :sem_saldo,
            nao_autorizado = :nao_autorizado,
            cpf_invalido   = :cpf_invalido,
            falha_consulta = :falha_consulta
           WHERE id = :session_id""",
        {**counters, "session_id": session_id}
    )
    conn.commit()
    conn.close()


def finish_session(session_id: int, status: str = "finished"):
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET finished_at = datetime('now','localtime'), status = ? WHERE id = ?",
        (status, session_id)
    )
    conn.commit()
    conn.close()


def add_result(session_id: int, cpf: str, valor: str, motivo: Optional[str]):
    conn = get_connection()
    conn.execute(
        """INSERT INTO session_results (session_id, cpf, valor, motivo, consulted_at)
           VALUES (?, ?, ?, ?, datetime('now','localtime'))""",
        (session_id, cpf, valor, motivo)
    )
    conn.commit()
    conn.close()


def get_recent_sessions(days: int = 7) -> List[dict]:
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """SELECT s.*, e.filepath as export_path, e.exported_at
           FROM sessions s
           LEFT JOIN exports e ON e.session_id = s.id
           WHERE s.started_at >= ?
           ORDER BY s.started_at DESC""",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_results(session_id: int) -> List[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT cpf, valor, motivo, consulted_at FROM session_results WHERE session_id = ? ORDER BY id",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_export(session_id: int, filename: str, filepath: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO exports (session_id, filename, filepath) VALUES (?, ?, ?)",
        (session_id, filename, filepath)
    )
    conn.commit()
    conn.close()


def cleanup_old_exports(days: int = 7):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    rows = conn.execute(
        "SELECT filepath FROM exports WHERE exported_at < ?", (cutoff,)
    ).fetchall()
    for row in rows:
        try:
            if os.path.exists(row["filepath"]):
                os.remove(row["filepath"])
        except OSError:
            pass
    conn.execute("DELETE FROM exports WHERE exported_at < ?", (cutoff,))
    conn.commit()
    conn.close()
