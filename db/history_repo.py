import os
from datetime import datetime, timedelta
from typing import List, Optional
from db.database import get_connection


def add_base(filename: str, filepath: str, tabela_id: str, tabela_nome: str, total_cpfs: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO bases (filename, filepath, tabela_id, tabela_nome, total_cpfs, uploaded_at)
           VALUES (?, ?, ?, ?, ?, datetime('now','localtime'))""",
        (filename, filepath, tabela_id, tabela_nome, total_cpfs)
    )
    conn.commit()
    base_id = cursor.lastrowid
    conn.close()
    return base_id


def get_base(base_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM bases WHERE id = ?", (base_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_base_counters(base_id: int, counters: dict):
    conn = get_connection()
    conn.execute(
        """UPDATE bases SET
            processed      = :processed,
            com_saldo      = :com_saldo,
            sem_saldo      = :sem_saldo,
            nao_autorizado = :nao_autorizado,
            cpf_invalido   = :cpf_invalido,
            falha_consulta = :falha_consulta
           WHERE id = :base_id""",
        {**counters, "base_id": base_id}
    )
    conn.commit()
    conn.close()


def reset_base(base_id: int):
    conn = get_connection()
    conn.execute(
        """UPDATE bases SET
            processed = 0, com_saldo = 0, sem_saldo = 0,
            nao_autorizado = 0, cpf_invalido = 0, falha_consulta = 0
           WHERE id = ?""",
        (base_id,)
    )
    conn.execute("DELETE FROM session_results WHERE base_id = ?", (base_id,))
    conn.commit()
    conn.close()


def add_result(base_id: int, cpf: str, valor: str, motivo: Optional[str]):
    conn = get_connection()
    conn.execute(
        """INSERT INTO session_results (base_id, cpf, valor, motivo, consulted_at)
           VALUES (?, ?, ?, ?, datetime('now','localtime'))""",
        (base_id, cpf, valor, motivo)
    )
    conn.commit()
    conn.close()


def delete_base(base_id: int):
    conn = get_connection()
    row = conn.execute("SELECT filepath FROM bases WHERE id = ?", (base_id,)).fetchone()
    if row:
        try:
            if os.path.exists(row["filepath"]):
                os.remove(row["filepath"])
        except OSError:
            pass
            
    exports = conn.execute("SELECT filepath FROM exports WHERE base_id = ?", (base_id,)).fetchall()
    for e in exports:
        try:
            if os.path.exists(e["filepath"]):
                os.remove(e["filepath"])
        except OSError:
            pass

    conn.execute("DELETE FROM session_results WHERE base_id = ?", (base_id,))
    conn.execute("DELETE FROM exports WHERE base_id = ?", (base_id,))
    conn.execute("DELETE FROM bases WHERE id = ?", (base_id,))
    conn.commit()
    conn.close()


def get_recent_bases(days: int = 7) -> List[dict]:
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """SELECT b.*, e.filepath as export_path, e.exported_at
           FROM bases b
           LEFT JOIN exports e ON e.base_id = b.id
           WHERE b.uploaded_at >= ?
           ORDER BY b.uploaded_at DESC""",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_base_results(base_id: int) -> List[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT cpf, valor, motivo, consulted_at FROM session_results WHERE base_id = ? ORDER BY id",
        (base_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_processed_cpfs(base_id: int) -> set[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT cpf FROM session_results WHERE base_id = ?",
        (base_id,)
    ).fetchall()
    conn.close()
    return {r["cpf"] for r in rows}


def add_export(base_id: int, filename: str, filepath: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO exports (base_id, filename, filepath) VALUES (?, ?, ?)",
        (base_id, filename, filepath)
    )
    conn.commit()
    conn.close()


def get_recent_exports(days: int = 7) -> List[dict]:
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """SELECT e.id, e.filename, e.filepath, e.exported_at,
                  b.filename as base_name, b.tabela_nome,
                  b.processed, b.com_saldo, b.sem_saldo, b.nao_autorizado,
                  b.cpf_invalido, b.falha_consulta, b.total_cpfs
           FROM exports e
           JOIN bases b ON b.id = e.base_id
           WHERE e.exported_at >= ?
           ORDER BY e.exported_at DESC""",
        (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cleanup_old_bases(days: int = 7):
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, filepath FROM bases WHERE uploaded_at < ?", (cutoff,)
    ).fetchall()
    
    for row in rows:
        # Tenta remover o arquivo físico
        try:
            if os.path.exists(row["filepath"]):
                os.remove(row["filepath"])
        except OSError:
            pass
            
        # Remove exports vinculados fisicamente
        exports = conn.execute("SELECT filepath FROM exports WHERE base_id = ?", (row["id"],)).fetchall()
        for e in exports:
            try:
                if os.path.exists(e["filepath"]):
                    os.remove(e["filepath"])
            except OSError:
                pass
                
        # Deleta as referências no DB (SQLite trata Foreign Keys mas é bom ser explícito sem PRAGMA foreign_keys)
        conn.execute("DELETE FROM session_results WHERE base_id = ?", (row["id"],))
        conn.execute("DELETE FROM exports WHERE base_id = ?", (row["id"],))
        conn.execute("DELETE FROM bases WHERE id = ?", (row["id"],))

    conn.commit()
    conn.close()
