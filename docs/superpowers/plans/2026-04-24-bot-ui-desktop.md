# Bot FGTS — UI Desktop (PyQt6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reescrever o bot de consulta FGTS como um aplicativo desktop PyQt6 com sidebar colapsável, worker pool multi-user, dashboard em tempo real, histórico de consultas em SQLite e exportação para Excel.

**Architecture:** Separação em três camadas — `core/` (lógica pura de API, sem UI), `db/` (SQLite via sqlite3 nativo), `ui/` (PyQt6). Workers rodam em QThread, comunicam com a UI via sinais Qt. A fila de CPFs é gerenciada por um QueueManager thread-safe. O `main.py` e `export.py` originais permanecem intocados na branch `master`.

**Tech Stack:** Python 3.x, PyQt6, SQLite3 (stdlib), openpyxl, requests, python-dotenv, PyInstaller

---

## Estrutura de Arquivos

```
BOT_PRINCIPAL/
├── app.py                          # Entry point — cria QApplication e abre MainWindow
├── requirements.txt                # Adicionar PyQt6
├── core/
│   ├── __init__.py
│   ├── api.py                      # get_token, consult_balance, simulation (portado do main.py)
│   ├── worker.py                   # QThread worker — consome fila de CPFs
│   └── queue_manager.py            # Fila thread-safe + controle pause/stop
├── db/
│   ├── __init__.py
│   ├── database.py                 # Conexão SQLite + criação de schema
│   ├── users_repo.py               # CRUD usuários V8
│   └── history_repo.py             # CRUD histórico de sessões + exportações
├── ui/
│   ├── __init__.py
│   ├── main_window.py              # Janela principal + sidebar + roteamento de páginas
│   ├── styles.py                   # QSS global com paleta de cores
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── dashboard.py            # Tela de consulta em andamento (métricas live)
│   │   ├── users_page.py           # Gerenciar usuários V8 (add/remove)
│   │   ├── base_page.py            # Carregar/trocar base XLSX
│   │   └── history_page.py         # Histórico + download de resultados
│   └── widgets/
│       ├── __init__.py
│       └── sidebar.py              # Sidebar colapsável com hover + ícones
├── assets/
│   └── icons/                      # SVGs/PNGs para sidebar (dashboard, users, base, history)
├── historico/                      # Gerado em runtime — xlsx salvos automaticamente
├── base/                           # XLSX de entrada (igual ao atual)
└── bot.db                          # SQLite gerado em runtime
```

---

## Task 1: Criar branch `ui` e instalar PyQt6

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Criar branch ui a partir do master**

```bash
git checkout master
git checkout -b ui
```

Expected: `Switched to a new branch 'ui'`

- [ ] **Step 2: Instalar PyQt6**

```bash
pip install PyQt6==6.7.0
```

Expected: `Successfully installed PyQt6-6.7.0`

- [ ] **Step 3: Adicionar PyQt6 ao requirements.txt**

Abrir `requirements.txt` e adicionar a linha:
```
PyQt6==6.7.0
```

- [ ] **Step 4: Verificar instalação**

```bash
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 OK')"
```

Expected: `PyQt6 OK`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "chore: add PyQt6 dependency, create ui branch"
```

---

## Task 2: Schema SQLite e repositórios

**Files:**
- Create: `db/__init__.py`
- Create: `db/database.py`
- Create: `db/users_repo.py`
- Create: `db/history_repo.py`

- [ ] **Step 1: Criar `db/__init__.py` vazio**

```python
```

- [ ] **Step 2: Criar `db/database.py`**

```python
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
```

- [ ] **Step 3: Criar `db/users_repo.py`**

```python
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
```

- [ ] **Step 4: Criar `db/history_repo.py`**

```python
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
```

- [ ] **Step 5: Verificar importações**

```bash
python -c "from db.database import init_db; init_db(); print('DB OK')"
```

Expected: `DB OK` e arquivo `bot.db` criado.

- [ ] **Step 6: Commit**

```bash
git add db/
git commit -m "feat: SQLite schema — users, sessions, results, exports"
```

---

## Task 3: Camada core — API e Queue Manager

**Files:**
- Create: `core/__init__.py`
- Create: `core/api.py`
- Create: `core/queue_manager.py`

- [ ] **Step 1: Criar `core/__init__.py` vazio**

```python
```

- [ ] **Step 2: Criar `core/api.py`** (lógica portada diretamente do `main.py` atual, sem prints de terminal)

```python
import time
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MAX_RETRIES = 25
TIMEOUT_SECONDS = 10

URL_AUTH_TOKEN     = 'https://auth.v8sistema.com/oauth/token'
URL_CONSULT_BALANCE = 'https://bff.v8sistema.com/fgts/balance'
URL_SIMULATION     = 'https://bff.v8sistema.com/fgts/simulations'

AUTH_AUDIENCE  = 'https://bff.v8sistema.com'
AUTH_CLIENT_ID = 'DHWogdaYmEI8n5bwwxPDzulMlSK7dwIn'
AUTH_SCOPE     = 'offline_access'
AUTH_GRANT_TYPE = 'password'
PROVIDER_BMS   = "bms"

TABELAS = {
    "1": {"nome": "Normal", "id": "cb563029-ba93-4b53-8d53-4ac145087212"},
    "2": {"nome": "Cometa", "id": "61c9fb2f-c902-4992-b8f5-b0ee368c45b0"},
}


class ConsultStatus(str, Enum):
    NAO_AUTORIZADO  = "NAO AUTORIZADO"
    SEM_SALDO       = "SEM SALDO"
    CPF_INVALIDO    = "CPF INVÁLIDO"
    FALHA_CONSULTA  = "FALHA CONSULTA"
    RETRY           = "RETRY"
    TOKEN_EXPIRADO  = "TOKEN EXPIRADO"


def get_token(username: str, password: str) -> Optional[str]:
    data = {
        'grant_type': AUTH_GRANT_TYPE,
        'username': username,
        'password': password,
        'audience': AUTH_AUDIENCE,
        'scope': AUTH_SCOPE,
        'client_id': AUTH_CLIENT_ID,
    }
    try:
        r = requests.post(URL_AUTH_TOKEN, data=data, timeout=TIMEOUT_SECONDS)
        r.raise_for_status()
        return r.json().get('access_token')
    except requests.RequestException as e:
        logging.error(f"Erro ao obter token: {e}")
        return None


def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(total=MAX_RETRIES, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session


def _handle_consult_error(response: requests.Response, cpf: str) -> Tuple[Any, Any, bool, Optional[str]]:
    try:
        raw = response.text
        try:
            body = response.json()
        except ValueError:
            logging.warning(f"CPF {cpf}: resposta não-JSON ({response.status_code}): {raw[:200]}")
            return ConsultStatus.RETRY, None, False, None
        error_msg = str(body.get('error', ''))

        if response.status_code == 400:
            detail = body.get('detail', '')
            if "não possui autorização" in detail or "Instituição Fiduciária" in detail:
                return ConsultStatus.NAO_AUTORIZADO, None, True, None
            if "não possui saldo disponível" in detail.lower():
                return ConsultStatus.SEM_SALDO, None, True, None
            return None, None, False, f"HTTP 400: {detail or error_msg}"

        if response.status_code == 500:
            if error_msg in ('values() must be called with at least one value',
                             "Saldo insuficiente, parcelas menores R$10,00."):
                return ConsultStatus.SEM_SALDO, None, True, None
            if error_msg == "Cannot read properties of undefined (reading 'map')":
                return ConsultStatus.NAO_AUTORIZADO, None, True, None
            if any(x in error_msg for x in [
                "Falha ao buscar o saldo disponivel!",
                "Serviço indisponivel no momento, tente novamente mais tarde",
                "Excedido o limite de requisições (máximo de 1 por segundo).",
                "Limite de requisições excedido, tente novamente mais tarde",
            ]):
                return ConsultStatus.RETRY, None, False, None
            if any(x in error_msg for x in ["Instituição Fiduciária", "Cliente não autorizou", "Empty response"]):
                return ConsultStatus.NAO_AUTORIZADO, None, True, None
            if "Número de CPF inválido" in error_msg:
                return ConsultStatus.CPF_INVALIDO, None, True, None
            if "Valor dos custos superior ao valor financiado" in error_msg or "Saldo insuficiente" in error_msg:
                return ConsultStatus.SEM_SALDO, None, True, None
            logging.error(f"Erro 500 desconhecido CPF {cpf}: {error_msg}")
            return None, None, False, f"HTTP 500: {error_msg}"

        return None, None, False, f"HTTP {response.status_code}: {response.text[:200]}"
    except Exception as e:
        return None, None, False, f"Erro ao processar resposta: {e}"


def consult_balance(
    session: requests.Session, token: str, cpf: str, averbador: str
) -> Tuple[Optional[List[Dict]], Optional[str], bool, Optional[str]]:
    headers = {'Authorization': f'Bearer {token}'}
    data = {"documentNumber": cpf, "provider": averbador}
    params = {"search": cpf, "status": "success", "page": 1, "limit": 1}

    retries = 0
    while retries < MAX_RETRIES:
        try:
            r = session.post(URL_CONSULT_BALANCE, headers=headers, json=data, timeout=TIMEOUT_SECONDS)
            r.raise_for_status()
            balance_data = r.json()

            if balance_data is None:
                poll = 0
                while poll < 15:
                    r = session.get(URL_CONSULT_BALANCE, headers=headers, params=params, timeout=TIMEOUT_SECONDS)
                    r.raise_for_status()
                    balance_data = r.json()
                    if balance_data and balance_data.get('data'):
                        break
                    time.sleep(2)
                    poll += 1

            if not balance_data:
                return None, None, False, "Resposta nula após polling"

            data_list = balance_data.get('data', [])
            if not data_list:
                return None, None, False, "data vazio após polling"

            first = data_list[0]
            periods = first.get('periods', [])
            balance_id = first.get('id')

            if not isinstance(periods, list):
                return None, None, False, "balance_periods inválido"

            new_periods = [
                {"totalAmount": a['amount'], "amount": a['amount'], "dueDate": a['dueDate']}
                for a in periods if isinstance(a, dict)
            ]
            return new_periods, balance_id, True, None

        except requests.RequestException as e:
            if getattr(e.response, 'status_code', None) == 429:
                time.sleep(2)
                retries += 1
                continue
            if e.response is not None:
                if e.response.status_code == 401:
                    return ConsultStatus.TOKEN_EXPIRADO, None, False, None
                result, b_id, finished, reason = _handle_consult_error(e.response, cpf)
                if result == ConsultStatus.RETRY:
                    time.sleep(0.4)
                    retries += 1
                    continue
                if finished:
                    return result, b_id, True, None
                return None, None, False, reason
            time.sleep(2)
            retries += 1
            continue
        except Exception as e:
            logging.error(f"Exceção consulta CPF {cpf}: {e}", exc_info=True)
            retries += 1
            continue

    return None, None, False, "Máximo de tentativas atingido"


def simulation(
    session: requests.Session, token: str, list_balance: List[Dict],
    cpf: str, balance_id: str, fees_id: str
) -> Optional[float]:
    headers = {'Authorization': f'Bearer {token}'}
    data = {
        "documentNumber": cpf,
        "isInsured": False,
        "simulationFeesId": fees_id,
        "targetAmount": 0,
        "provider": PROVIDER_BMS,
        "desiredInstallments": list_balance,
        "balanceId": balance_id,
    }

    retries = 0
    while retries < MAX_RETRIES:
        try:
            r = session.post(URL_SIMULATION, headers=headers, json=data, timeout=TIMEOUT_SECONDS)
            if r.status_code >= 400:
                try:
                    body = r.json()
                    logging.error(f"CPF {cpf}: erro simulação ({r.status_code}): {body.get('error') or body.get('detail')}")
                except ValueError:
                    pass
                if r.status_code in (500, 502, 503, 504):
                    time.sleep(2)
                    retries += 1
                    continue
                r.raise_for_status()
            sim = r.json()
            return sim.get('availableBalance')
        except requests.RequestException as e:
            if getattr(e.response, 'status_code', None) == 429:
                time.sleep(2)
                retries += 1
                continue
            if getattr(e, 'response', None) is None:
                time.sleep(2)
                retries += 1
                continue
            logging.error(f"Erro fatal simulação CPF {cpf}: {e}")
            break

    return None


def process_cpf(
    cpf: str, token: str, session: requests.Session, fees_id: str
) -> Tuple[str, Union[str, float, ConsultStatus], Optional[str]]:
    time.sleep(2)
    balance, balance_id, success, reason = consult_balance(session, token, cpf, PROVIDER_BMS)

    if balance == ConsultStatus.TOKEN_EXPIRADO:
        return cpf, ConsultStatus.TOKEN_EXPIRADO, None

    if success and balance in (ConsultStatus.NAO_AUTORIZADO, ConsultStatus.CPF_INVALIDO):
        return cpf, balance.value, None

    if success and balance not in (ConsultStatus.SEM_SALDO, None):
        if len(balance) < 2:
            return cpf, ConsultStatus.SEM_SALDO.value, None
        sim = simulation(session, token, balance, cpf, balance_id, fees_id)
        if sim is not None:
            return cpf, sim, None
        return cpf, ConsultStatus.FALHA_CONSULTA.value, "Simulação não retornou saldo"

    if not success:
        return cpf, ConsultStatus.FALHA_CONSULTA.value, reason

    return cpf, ConsultStatus.SEM_SALDO.value, None
```

- [ ] **Step 3: Criar `core/queue_manager.py`**

```python
import threading
from typing import List, Optional


class QueueManager:
    """Thread-safe CPF queue with pause/stop controls."""

    def __init__(self, cpfs: List[str]):
        self._cpfs = list(cpfs)
        self._index = 0
        self._lock = threading.Lock()
        self._pause_event = threading.Event()
        self._stop_event = threading.Event()
        self._pause_event.set()  # not paused by default

    def next_cpf(self) -> Optional[str]:
        """Returns next CPF or None if queue is exhausted or stopped."""
        self._pause_event.wait()  # blocks if paused
        if self._stop_event.is_set():
            return None
        with self._lock:
            if self._index >= len(self._cpfs):
                return None
            cpf = self._cpfs[self._index]
            self._index += 1
            return cpf

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def stop(self):
        self._stop_event.set()
        self._pause_event.set()  # unblock any waiting workers

    @property
    def is_paused(self) -> bool:
        return not self._pause_event.is_set()

    @property
    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    @property
    def progress(self) -> int:
        return self._index

    @property
    def total(self) -> int:
        return len(self._cpfs)
```

- [ ] **Step 4: Verificar importações**

```bash
python -c "from core.api import get_token, ConsultStatus; from core.queue_manager import QueueManager; print('Core OK')"
```

Expected: `Core OK`

- [ ] **Step 5: Commit**

```bash
git add core/
git commit -m "feat: core layer — API port + thread-safe queue manager"
```

---

## Task 4: Worker QThread

**Files:**
- Create: `core/worker.py`

- [ ] **Step 1: Criar `core/worker.py`**

```python
import logging
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal
from core.api import (
    ConsultStatus, create_session, get_token, process_cpf, TABELAS
)
from core.queue_manager import QueueManager
from db import history_repo


class CpfWorker(QThread):
    result_ready = pyqtSignal(str, str, object)   # cpf, status_label, valor
    token_renewed = pyqtSignal(int)               # worker_id
    finished_worker = pyqtSignal(int)             # worker_id

    def __init__(
        self,
        worker_id: int,
        username: str,
        password: str,
        fees_id: str,
        queue: QueueManager,
        session_id: int,
        parent=None
    ):
        super().__init__(parent)
        self.worker_id = worker_id
        self.username = username
        self.password = password
        self.fees_id = fees_id
        self.queue = queue
        self.session_id = session_id

    def run(self):
        token = get_token(self.username, self.password)
        if not token:
            logging.error(f"Worker {self.worker_id}: falha ao obter token.")
            self.finished_worker.emit(self.worker_id)
            return

        http_session = create_session()

        while True:
            cpf = self.queue.next_cpf()
            if cpf is None:
                break

            cpf_str, result, reason = process_cpf(cpf, token, http_session, self.fees_id)

            if result == ConsultStatus.TOKEN_EXPIRADO:
                token = get_token(self.username, self.password)
                if not token:
                    logging.error(f"Worker {self.worker_id}: falha ao renovar token.")
                    break
                self.token_renewed.emit(self.worker_id)
                cpf_str, result, reason = process_cpf(cpf, token, http_session, self.fees_id)

            valor_str = str(result) if not isinstance(result, float) else f"{result:.2f}"
            history_repo.add_result(self.session_id, cpf_str, valor_str, reason)
            self.result_ready.emit(cpf_str, valor_str, reason)

        self.finished_worker.emit(self.worker_id)
```

- [ ] **Step 2: Verificar importação**

```bash
python -c "from core.worker import CpfWorker; print('Worker OK')"
```

Expected: `Worker OK`

- [ ] **Step 3: Commit**

```bash
git add core/worker.py
git commit -m "feat: CpfWorker QThread — worker pool consumer"
```

---

## Task 5: Estilos QSS globais

**Files:**
- Create: `ui/__init__.py`
- Create: `ui/styles.py`
- Create: `ui/pages/__init__.py`
- Create: `ui/widgets/__init__.py`

- [ ] **Step 1: Criar arquivos `__init__.py` vazios**

Criar os três arquivos a seguir com conteúdo vazio:
- `ui/__init__.py`
- `ui/pages/__init__.py`
- `ui/widgets/__init__.py`

- [ ] **Step 2: Criar `ui/styles.py`**

```python
# Paleta: #380F17 vinho | #8F0B13 vermelho | #EFDFC5 creme | #252B2B chumbo | #4C4F54 cinza

STYLESHEET = """
/* ── Base ── */
QWidget {
    background-color: #252B2B;
    color: #EFDFC5;
    font-family: 'Segoe UI';
    font-size: 13px;
}

QMainWindow {
    background-color: #252B2B;
}

/* ── Sidebar ── */
#sidebar {
    background-color: #380F17;
    border-right: 1px solid #4C4F54;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #EFDFC5;
    border: none;
    text-align: left;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 13px;
}

#sidebar QPushButton:hover {
    background-color: #8F0B13;
}

#sidebar QPushButton:checked {
    background-color: #8F0B13;
    font-weight: bold;
}

/* ── Cards / Painéis ── */
#card {
    background-color: #2E3535;
    border: 1px solid #4C4F54;
    border-radius: 8px;
    padding: 12px;
}

/* ── Botões de ação ── */
QPushButton {
    background-color: #8F0B13;
    color: #EFDFC5;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #B01020;
}

QPushButton:disabled {
    background-color: #4C4F54;
    color: #888;
}

QPushButton#btnDanger {
    background-color: #380F17;
    border: 1px solid #8F0B13;
}

QPushButton#btnDanger:hover {
    background-color: #8F0B13;
}

/* ── Inputs ── */
QLineEdit {
    background-color: #2E3535;
    color: #EFDFC5;
    border: 1px solid #4C4F54;
    border-radius: 5px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border: 1px solid #8F0B13;
}

/* ── Tabelas ── */
QTableWidget {
    background-color: #252B2B;
    gridline-color: #4C4F54;
    border: none;
}

QTableWidget::item {
    padding: 6px;
}

QTableWidget::item:selected {
    background-color: #8F0B13;
    color: #EFDFC5;
}

QHeaderView::section {
    background-color: #380F17;
    color: #EFDFC5;
    padding: 6px;
    border: none;
    font-weight: bold;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #252B2B;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #4C4F54;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #8F0B13;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── ComboBox ── */
QComboBox {
    background-color: #2E3535;
    color: #EFDFC5;
    border: 1px solid #4C4F54;
    border-radius: 5px;
    padding: 5px 10px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #2E3535;
    color: #EFDFC5;
    selection-background-color: #8F0B13;
}

/* ── Labels de status ── */
QLabel#statusRunning  { color: #4CAF50; font-weight: bold; }
QLabel#statusPaused   { color: #FFC107; font-weight: bold; }
QLabel#statusStopped  { color: #8F0B13; font-weight: bold; }
QLabel#metricValue    { color: #EFDFC5; font-size: 22px; font-weight: bold; }
QLabel#metricLabel    { color: #4C4F54; font-size: 11px; }
"""
```

- [ ] **Step 3: Verificar importação**

```bash
python -c "from ui.styles import STYLESHEET; print('Styles OK', len(STYLESHEET), 'chars')"
```

Expected: `Styles OK` seguido do número de caracteres.

- [ ] **Step 4: Commit**

```bash
git add ui/
git commit -m "feat: QSS stylesheet with brand palette"
```

---

## Task 6: Sidebar colapsável

**Files:**
- Create: `ui/widgets/sidebar.py`

- [ ] **Step 1: Criar `ui/widgets/sidebar.py`**

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QSizePolicy
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtSignal, QSize, Qt
from PyQt6.QtGui import QIcon


SIDEBAR_COLLAPSED = 56
SIDEBAR_EXPANDED  = 200

NAV_ITEMS = [
    ("dashboard", "Dashboard",  "assets/icons/dashboard.png"),
    ("users",     "Usuários",   "assets/icons/users.png"),
    ("base",      "Base",       "assets/icons/base.png"),
    ("history",   "Histórico",  "assets/icons/history.png"),
]


class Sidebar(QWidget):
    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_COLLAPSED)
        self._expanded = False
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(4)

        for key, label, icon_path in NAV_ITEMS:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(22, 22))
            btn.setToolTip(label)
            btn.clicked.connect(lambda checked, k=key: self._on_nav(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()
        self._buttons["dashboard"].setChecked(True)

    def _on_nav(self, key: str):
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)
        self.page_changed.emit(key)

    def expand(self):
        if self._expanded:
            return
        self._expanded = True
        self._animate(SIDEBAR_EXPANDED)
        for key, label, _ in NAV_ITEMS:
            self._buttons[key].setText(f"  {label}")

    def collapse(self):
        if not self._expanded:
            return
        self._expanded = False
        self._animate(SIDEBAR_COLLAPSED)
        for key, _, _ in NAV_ITEMS:
            self._buttons[key].setText("")

    def _animate(self, target_width: int):
        anim = QPropertyAnimation(self, b"minimumWidth", self)
        anim.setDuration(180)
        anim.setEndValue(target_width)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim2 = QPropertyAnimation(self, b"maximumWidth", self)
        anim2.setDuration(180)
        anim2.setEndValue(target_width)
        anim2.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        anim2.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def enterEvent(self, event):
        self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.collapse()
        super().leaveEvent(event)
```

- [ ] **Step 2: Criar ícones placeholder** (arquivos PNG 24x24 vazios para não quebrar o import)

```bash
mkdir -p assets/icons
python -c "
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
for name in ['dashboard','users','base','history']:
    px = QPixmap(24,24)
    px.fill(QColor('#EFDFC5'))
    px.save(f'assets/icons/{name}.png')
print('Icons OK')
"
```

Expected: `Icons OK` e 4 arquivos PNG criados em `assets/icons/`.

- [ ] **Step 3: Verificar importação**

```bash
python -c "from PyQt6.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); from ui.widgets.sidebar import Sidebar; s=Sidebar(); print('Sidebar OK')"
```

Expected: `Sidebar OK`

- [ ] **Step 4: Commit**

```bash
git add ui/widgets/sidebar.py assets/
git commit -m "feat: collapsible sidebar with hover animation"
```

---

## Task 7: Página de Usuários V8

**Files:**
- Create: `ui/pages/users_page.py`

- [ ] **Step 1: Criar `ui/pages/users_page.py`**

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from db import users_repo


class UsersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.load_users()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Usuários V8")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #EFDFC5;")
        root.addWidget(title)

        # Formulário de adição
        form = QHBoxLayout()
        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Usuário V8")
        self.input_pass = QLineEdit()
        self.input_pass.setPlaceholderText("Senha V8")
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        btn_add = QPushButton("Adicionar")
        btn_add.clicked.connect(self._add_user)
        form.addWidget(self.input_user)
        form.addWidget(self.input_pass)
        form.addWidget(btn_add)
        root.addLayout(form)

        # Tabela de usuários
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Usuário", "Ação"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self.table)

    def load_users(self):
        self.table.setRowCount(0)
        for user in users_repo.list_users():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
            self.table.setItem(row, 1, QTableWidgetItem(user["username"]))
            btn_del = QPushButton("Remover")
            btn_del.setObjectName("btnDanger")
            btn_del.clicked.connect(lambda _, uid=user["id"]: self._remove_user(uid))
            self.table.setCellWidget(row, 2, btn_del)

    def _add_user(self):
        username = self.input_user.text().strip()
        password = self.input_pass.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Atenção", "Preencha usuário e senha.")
            return
        try:
            users_repo.add_user(username, password)
            self.input_user.clear()
            self.input_pass.clear()
            self.load_users()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Usuário já existe ou erro: {e}")

    def _remove_user(self, user_id: int):
        reply = QMessageBox.question(
            self, "Confirmar", "Remover este usuário?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            users_repo.remove_user(user_id)
            self.load_users()
```

- [ ] **Step 2: Verificar importação**

```bash
python -c "from PyQt6.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); from ui.pages.users_page import UsersPage; p=UsersPage(); print('UsersPage OK')"
```

Expected: `UsersPage OK`

- [ ] **Step 3: Commit**

```bash
git add ui/pages/users_page.py
git commit -m "feat: users page — add/remove V8 users"
```

---

## Task 8: Página de Base XLSX

**Files:**
- Create: `ui/pages/base_page.py`

- [ ] **Step 1: Criar `ui/pages/base_page.py`**

```python
import os
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QComboBox
)
from PyQt6.QtCore import pyqtSignal
from core.api import TABELAS

BASE_DIR = "base"


class BasePage(QWidget):
    base_configured = pyqtSignal(str, str, str)  # filepath, filename, tabela_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._refresh_current()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Base de Consulta")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #EFDFC5;")
        root.addWidget(title)

        # Arquivo atual
        self.lbl_current = QLabel("Nenhuma base carregada")
        self.lbl_current.setStyleSheet("color: #4C4F54; font-size: 12px;")
        root.addWidget(self.lbl_current)

        # Botão de seleção
        btn_row = QHBoxLayout()
        btn_select = QPushButton("Selecionar arquivo XLSX")
        btn_select.clicked.connect(self._select_file)
        btn_row.addWidget(btn_select)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Tabela de simulação
        tab_row = QHBoxLayout()
        tab_row.addWidget(QLabel("Tabela de simulação:"))
        self.combo_tabela = QComboBox()
        for key, val in TABELAS.items():
            self.combo_tabela.addItem(val["nome"], val["id"])
        tab_row.addWidget(self.combo_tabela)
        tab_row.addStretch()
        root.addLayout(tab_row)

        root.addStretch()

    def _refresh_current(self):
        os.makedirs(BASE_DIR, exist_ok=True)
        files = [f for f in os.listdir(BASE_DIR) if not f.startswith('~$') and f.endswith('.xlsx')]
        if files:
            self.lbl_current.setText(f"Base atual: {files[0]}")
            self.lbl_current.setStyleSheet("color: #EFDFC5; font-size: 12px;")
        else:
            self.lbl_current.setText("Nenhuma base carregada")
            self.lbl_current.setStyleSheet("color: #4C4F54; font-size: 12px;")

    def _select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar base XLSX", "", "Excel Files (*.xlsx)"
        )
        if not path:
            return
        os.makedirs(BASE_DIR, exist_ok=True)
        # Remove arquivo anterior
        for old in os.listdir(BASE_DIR):
            if not old.startswith('~$'):
                os.remove(os.path.join(BASE_DIR, old))
        dest = os.path.join(BASE_DIR, os.path.basename(path))
        shutil.copy2(path, dest)
        self._refresh_current()
        tabela_id = self.combo_tabela.currentData()
        tabela_nome = self.combo_tabela.currentText()
        self.base_configured.emit(dest, os.path.basename(path), tabela_id)
        QMessageBox.information(self, "Sucesso", f"Base '{os.path.basename(path)}' carregada.\nTabela: {tabela_nome}")

    def get_current_config(self):
        """Returns (filepath, filename, tabela_id) or None if no base loaded."""
        files = [f for f in os.listdir(BASE_DIR) if not f.startswith('~$') and f.endswith('.xlsx')]
        if not files:
            return None
        filepath = os.path.join(BASE_DIR, files[0])
        tabela_id = self.combo_tabela.currentData()
        return filepath, files[0], tabela_id
```

- [ ] **Step 2: Verificar importação**

```bash
python -c "from PyQt6.QtWidgets import QApplication; import sys; app=QApplication(sys.argv); from ui.pages.base_page import BasePage; p=BasePage(); print('BasePage OK')"
```

Expected: `BasePage OK`

- [ ] **Step 3: Commit**

```bash
git add ui/pages/base_page.py
git commit -m "feat: base page — load/swap XLSX and select simulation table"
```

---

## Task 9: Página de Dashboard (consulta em andamento)

**Files:**
- Create: `ui/pages/dashboard.py`

- [ ] **Step 1: Criar `ui/pages/dashboard.py`**

```python
import os
import openpyxl
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGridLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSlot
from core.api import TABELAS, ConsultStatus
from core.queue_manager import QueueManager
from core.worker import CpfWorker
from db import history_repo, users_repo
from db.database import init_db

BASE_DIR = "base"
HISTORICO_DIR = "historico"


def _metric_card(label: str) -> tuple[QWidget, QLabel]:
    card = QFrame()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    val_lbl = QLabel("0")
    val_lbl.setObjectName("metricValue")
    val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl = QLabel(label)
    lbl.setObjectName("metricLabel")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(val_lbl)
    lay.addWidget(lbl)
    return card, val_lbl


class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        init_db()
        self._workers: list[CpfWorker] = []
        self._queue: QueueManager | None = None
        self._session_id: int | None = None
        self._counters = {
            "processed": 0, "com_saldo": 0, "sem_saldo": 0,
            "nao_autorizado": 0, "cpf_invalido": 0, "falha_consulta": 0
        }
        self._workers_done = 0
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #EFDFC5;")
        root.addWidget(title)

        # Status e controles
        ctrl = QHBoxLayout()
        self.lbl_status = QLabel("Aguardando")
        self.lbl_status.setObjectName("statusStopped")
        ctrl.addWidget(self.lbl_status)
        ctrl.addStretch()
        self.btn_start  = QPushButton("Iniciar")
        self.btn_pause  = QPushButton("Pausar")
        self.btn_stop   = QPushButton("Parar")
        self.btn_export = QPushButton("Exportar Excel")
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.btn_start.clicked.connect(self._start)
        self.btn_pause.clicked.connect(self._pause_resume)
        self.btn_stop.clicked.connect(self._stop)
        self.btn_export.clicked.connect(self._export)
        for b in (self.btn_start, self.btn_pause, self.btn_stop, self.btn_export):
            ctrl.addWidget(b)
        root.addLayout(ctrl)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #4C4F54; border-radius: 5px; background: #2E3535; text-align: center; color: #EFDFC5; }
            QProgressBar::chunk { background-color: #8F0B13; border-radius: 4px; }
        """)
        root.addWidget(self.progress)

        # Cards de métricas
        grid = QGridLayout()
        grid.setSpacing(12)
        cards_data = [
            ("Processados",    "processed"),
            ("Com Saldo",      "com_saldo"),
            ("Sem Saldo",      "sem_saldo"),
            ("Não Autorizado", "nao_autorizado"),
            ("CPF Inválido",   "cpf_invalido"),
            ("Falha Consulta", "falha_consulta"),
        ]
        self._metric_labels: dict[str, QLabel] = {}
        for i, (label, key) in enumerate(cards_data):
            card, val_lbl = _metric_card(label)
            self._metric_labels[key] = val_lbl
            grid.addWidget(card, i // 3, i % 3)
        root.addLayout(grid)

        # Tabela de resultados ao vivo
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["CPF", "Resultado", "Motivo"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(self.table)

    def set_base_config(self, filepath: str, filename: str, tabela_id: str):
        self._base_filepath = filepath
        self._base_filename = filename
        self._tabela_id = tabela_id

    def _load_cpfs(self) -> list[str]:
        files = [f for f in os.listdir(BASE_DIR) if not f.startswith('~$') and f.endswith('.xlsx')]
        if not files:
            return []
        wb = openpyxl.load_workbook(os.path.join(BASE_DIR, files[0]))
        sheet = wb.active
        return [str(row[0]) for row in sheet.iter_rows(min_row=2, max_col=1, values_only=True) if row[0]]

    def _start(self):
        users = users_repo.list_users()
        if not users:
            QMessageBox.warning(self, "Atenção", "Adicione ao menos um usuário V8 antes de iniciar.")
            return

        cpfs = self._load_cpfs()
        if not cpfs:
            QMessageBox.warning(self, "Atenção", "Nenhuma base XLSX carregada ou base vazia.")
            return

        tabela_id = getattr(self, '_tabela_id', list(TABELAS.values())[0]["id"])
        base_filename = getattr(self, '_base_filename', os.listdir(BASE_DIR)[0])

        tabela_nome = next((t["nome"] for t in TABELAS.values() if t["id"] == tabela_id), "Normal")
        self._session_id = history_repo.create_session(base_filename, tabela_nome, len(cpfs))

        self._counters = {k: 0 for k in self._counters}
        self._workers_done = 0
        self.table.setRowCount(0)
        self.progress.setMaximum(len(cpfs))
        self.progress.setValue(0)

        self._queue = QueueManager(cpfs)
        self._workers = []
        for user in users:
            creds = users_repo.get_user_credentials(user["id"])
            worker = CpfWorker(
                worker_id=user["id"],
                username=creds["username"],
                password=creds["password"],
                fees_id=tabela_id,
                queue=self._queue,
                session_id=self._session_id,
            )
            worker.result_ready.connect(self._on_result)
            worker.finished_worker.connect(self._on_worker_done)
            self._workers.append(worker)

        for w in self._workers:
            w.start()

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.lbl_status.setText("Rodando")
        self.lbl_status.setObjectName("statusRunning")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def _pause_resume(self):
        if self._queue is None:
            return
        if self._queue.is_paused:
            self._queue.resume()
            self.btn_pause.setText("Pausar")
            self.lbl_status.setText("Rodando")
            self.lbl_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self._queue.pause()
            self.btn_pause.setText("Retomar")
            self.lbl_status.setText("Pausado")
            self.lbl_status.setStyleSheet("color: #FFC107; font-weight: bold;")

    def _stop(self):
        if self._queue:
            self._queue.stop()
        self.lbl_status.setText("Parando...")
        self.lbl_status.setStyleSheet("color: #8F0B13; font-weight: bold;")
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

    @pyqtSlot(str, str, object)
    def _on_result(self, cpf: str, valor: str, motivo):
        # Atualiza contadores
        c = self._counters
        c["processed"] += 1
        try:
            float(valor)
            c["com_saldo"] += 1
        except ValueError:
            if valor == ConsultStatus.SEM_SALDO.value:
                c["sem_saldo"] += 1
            elif valor == ConsultStatus.NAO_AUTORIZADO.value:
                c["nao_autorizado"] += 1
            elif valor == ConsultStatus.CPF_INVALIDO.value:
                c["cpf_invalido"] += 1
            else:
                c["falha_consulta"] += 1

        for key, lbl in self._metric_labels.items():
            lbl.setText(str(c[key]))

        self.progress.setValue(c["processed"])

        # Persiste no SQLite
        if self._session_id:
            history_repo.update_session_counters(self._session_id, {**c, "session_id": self._session_id})

        # Adiciona linha à tabela ao vivo
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(cpf))
        self.table.setItem(row, 1, QTableWidgetItem(valor))
        self.table.setItem(row, 2, QTableWidgetItem(str(motivo or "")))
        self.table.scrollToBottom()

    @pyqtSlot(int)
    def _on_worker_done(self, worker_id: int):
        self._workers_done += 1
        if self._workers_done >= len(self._workers):
            self._all_done()

    def _all_done(self):
        if self._session_id:
            history_repo.finish_session(self._session_id)
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(True)
        self.btn_pause.setText("Pausar")
        self.lbl_status.setText("Concluído")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def _export(self):
        if self._session_id is None:
            return
        from core.exporter import export_session
        os.makedirs(HISTORICO_DIR, exist_ok=True)
        results = history_repo.get_session_results(self._session_id)
        session_info = {
            "base_name": getattr(self, '_base_filename', '-'),
            "tabela_simulacao": "-",
            "processed": self._counters["processed"],
            "com_saldo": self._counters["com_saldo"],
            "sem_saldo": self._counters["sem_saldo"],
            "nao_autorizado": self._counters["nao_autorizado"],
            "cpf_invalido": self._counters["cpf_invalido"],
            "falha_consulta": self._counters["falha_consulta"],
        }
        filename = f"Saldos_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.xlsx"
        filepath = os.path.join(HISTORICO_DIR, filename)
        export_session(results, session_info, filepath)
        history_repo.add_export(self._session_id, filename, filepath)
        QMessageBox.information(self, "Exportado", f"Resultado salvo em:\n{filepath}")
        self.btn_export.setEnabled(False)
```

- [ ] **Step 2: Commit**

```bash
git add ui/pages/dashboard.py
git commit -m "feat: dashboard page — live metrics, worker pool controls, export"
```

---

## Task 10: Exportador (core/exporter.py)

**Files:**
- Create: `core/exporter.py`

- [ ] **Step 1: Criar `core/exporter.py`**

```python
import os
from typing import List, Dict
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

FONT_NAME = 'Calibri'
COR_HEADER  = 'C8A2C8'
COR_SALDO   = 'C6EFCE'
COR_SEM     = 'FCE4D6'
COR_NAO_AUT = 'FFEB9C'
COR_FALHA   = 'FFC7CE'
COR_NEUTRO  = 'FFFFFF'
COR_RES_HDR = '4472C4'
COR_RES_BDY = 'DDEEFF'


def _font(bold=False, color='000000', size=11):
    return Font(name=FONT_NAME, bold=bold, color=color, size=size)

def _fill(hex_color):
    return PatternFill(fill_type='solid', fgColor=hex_color)

def _border():
    s = Side(style='thin', color='CCCCCC')
    return Border(left=s, right=s, top=s, bottom=s)

def _cell(cell, value, bold=False, font_color='000000', bg=None, align='left'):
    cell.value = value
    cell.font = _font(bold=bold, color=font_color)
    cell.alignment = Alignment(horizontal=align, vertical='center', wrap_text=True)
    if bg:
        cell.fill = _fill(bg)
    cell.border = _border()

def _row_color(valor) -> str:
    try:
        float(valor)
        return COR_SALDO
    except (ValueError, TypeError):
        pass
    v = str(valor)
    if v == 'SEM SALDO':      return COR_SEM
    if v == 'NAO AUTORIZADO': return COR_NAO_AUT
    if v == 'FALHA CONSULTA': return COR_FALHA
    return COR_NEUTRO


def export_session(results: List[Dict], session_info: Dict, output_path: str):
    """
    results: list of dicts with keys cpf, valor, motivo, consulted_at
    session_info: dict with base_name, tabela_simulacao, processed, com_saldo, etc.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.sheet_view.showGridLines = False

    has_motivo = any(r.get("motivo") for r in results)
    if has_motivo:
        col_f, col_v = 'F', 'G'
        ws.column_dimensions['C'].width = 52
        ws.column_dimensions['D'].width = 20
        ws.column_dimensions['E'].width = 2
        ws.column_dimensions['F'].width = 26
        ws.column_dimensions['G'].width = 26
    else:
        col_f, col_v = 'E', 'F'
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 2
        ws.column_dimensions['E'].width = 26
        ws.column_dimensions['F'].width = 26

    ws.column_dimensions['A'].width = 16
    ws.column_dimensions['B'].width = 16

    _cell(ws['A1'], 'CPF',   bold=True, font_color='FFFFFF', bg=COR_HEADER)
    _cell(ws['B1'], 'Valor', bold=True, font_color='FFFFFF', bg=COR_HEADER)
    if has_motivo:
        _cell(ws['C1'], 'Motivo da Falha', bold=True, font_color='FFFFFF', bg=COR_HEADER)
        _cell(ws['D1'], 'Data e Hora',     bold=True, font_color='FFFFFF', bg=COR_HEADER)
    else:
        _cell(ws['C1'], 'Data e Hora', bold=True, font_color='FFFFFF', bg=COR_HEADER)

    for i, r in enumerate(results, start=2):
        bg = _row_color(r["valor"])
        valor = r["valor"]
        try:
            fval = float(valor)
            display = f"R$ {fval:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            display = valor
        _cell(ws[f'A{i}'], r["cpf"],   bg=bg)
        _cell(ws[f'B{i}'], display,    bg=bg, align='center')
        if has_motivo:
            _cell(ws[f'C{i}'], r.get("motivo") or '', bg=bg)
            _cell(ws[f'D{i}'], r.get("consulted_at", ''), bg=bg, align='center')
        else:
            _cell(ws[f'C{i}'], r.get("consulted_at", ''), bg=bg, align='center')

    resumo = [
        ("Base processada",     session_info.get("base_name", "-")),
        ("Tabela de simulação", session_info.get("tabela_simulacao", "-")),
        ("CPFs processados",    session_info.get("processed", 0)),
        ("Com saldo",           session_info.get("com_saldo", 0)),
        ("Sem saldo",           session_info.get("sem_saldo", 0)),
        ("Não autorizado",      session_info.get("nao_autorizado", 0)),
        ("CPF inválido",        session_info.get("cpf_invalido", 0)),
        ("Falha de consulta",   session_info.get("falha_consulta", 0)),
    ]
    _cell(ws[f'{col_f}1'], 'Campo', bold=True, font_color='FFFFFF', bg=COR_RES_HDR)
    _cell(ws[f'{col_v}1'], 'Valor', bold=True, font_color='FFFFFF', bg=COR_RES_HDR)
    for i, (campo, valor) in enumerate(resumo, start=2):
        _cell(ws[f'{col_f}{i}'], campo, bg=COR_RES_BDY)
        _cell(ws[f'{col_v}{i}'], valor, bg=COR_RES_BDY, align='center')

    ws.freeze_panes = 'A2'
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    wb.save(output_path)
```

- [ ] **Step 2: Verificar importação**

```bash
python -c "from core.exporter import export_session; print('Exporter OK')"
```

Expected: `Exporter OK`

- [ ] **Step 3: Commit**

```bash
git add core/exporter.py
git commit -m "feat: exporter — generate Excel from session results"
```

---

## Task 11: Página de Histórico

**Files:**
- Create: `ui/pages/history_page.py`

- [ ] **Step 1: Criar `ui/pages/history_page.py`**

```python
import os
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from db import history_repo


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.load_history()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Histórico de Consultas (últimos 7 dias)")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #EFDFC5;")
        btn_refresh = QPushButton("Atualizar")
        btn_refresh.clicked.connect(self.load_history)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_refresh)
        root.addLayout(header)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Data", "Base", "Tabela", "Total", "Saldos",
            "Sem Saldo", "Não Aut.", "Ação"
        ])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self.table)

    def load_history(self):
        self.table.setRowCount(0)
        sessions = history_repo.get_recent_sessions(days=7)
        for s in sessions:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(s.get("started_at", ""))[:16]))
            self.table.setItem(row, 1, QTableWidgetItem(str(s.get("base_name", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(s.get("tabela_simulacao", ""))))
            self.table.setItem(row, 3, QTableWidgetItem(str(s.get("processed", 0))))
            self.table.setItem(row, 4, QTableWidgetItem(str(s.get("com_saldo", 0))))
            self.table.setItem(row, 5, QTableWidgetItem(str(s.get("sem_saldo", 0))))
            self.table.setItem(row, 6, QTableWidgetItem(str(s.get("nao_autorizado", 0))))

            export_path = s.get("export_path")
            btn = QPushButton("Baixar" if export_path and os.path.exists(str(export_path)) else "Sem exportação")
            btn.setEnabled(bool(export_path and os.path.exists(str(export_path))))
            if export_path:
                btn.clicked.connect(lambda _, p=export_path: self._download(p))
            self.table.setCellWidget(row, 7, btn)

    def _download(self, filepath: str):
        dest_dir = QFileDialog.getExistingDirectory(self, "Escolha a pasta de destino")
        if not dest_dir:
            return
        dest = os.path.join(dest_dir, os.path.basename(filepath))
        try:
            shutil.copy2(filepath, dest)
            QMessageBox.information(self, "Sucesso", f"Arquivo copiado para:\n{dest}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao copiar arquivo: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add ui/pages/history_page.py
git commit -m "feat: history page — list sessions, download exports"
```

---

## Task 12: Janela principal e entry point

**Files:**
- Create: `ui/main_window.py`
- Create: `app.py`

- [ ] **Step 1: Criar `ui/main_window.py`**

```python
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from PyQt6.QtCore import Qt
from ui.widgets.sidebar import Sidebar
from ui.pages.dashboard import DashboardPage
from ui.pages.users_page import UsersPage
from ui.pages.base_page import BasePage
from ui.pages.history_page import HistoryPage
from ui.styles import STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BOT FGTS")
        self.setMinimumSize(1000, 660)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._switch_page)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.dashboard = DashboardPage()
        self.users_page = UsersPage()
        self.base_page = BasePage()
        self.history_page = HistoryPage()

        self.stack.addWidget(self.dashboard)   # index 0
        self.stack.addWidget(self.users_page)  # index 1
        self.stack.addWidget(self.base_page)   # index 2
        self.stack.addWidget(self.history_page) # index 3

        self.base_page.base_configured.connect(self.dashboard.set_base_config)

        self._pages = {
            "dashboard": 0,
            "users":     1,
            "base":      2,
            "history":   3,
        }

    def _switch_page(self, key: str):
        idx = self._pages.get(key, 0)
        self.stack.setCurrentIndex(idx)
        if key == "history":
            self.history_page.load_history()
```

- [ ] **Step 2: Criar `app.py`**

```python
import sys
from PyQt6.QtWidgets import QApplication
from db.database import init_db
from db.history_repo import cleanup_old_exports
from ui.main_window import MainWindow


def main():
    init_db()
    cleanup_old_exports(days=7)
    app = QApplication(sys.argv)
    app.setApplicationName("BOT FGTS")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Testar execução do app**

```bash
python app.py
```

Expected: Janela abre com sidebar, todas as páginas navegáveis, sem erros no terminal.

- [ ] **Step 4: Commit**

```bash
git add ui/main_window.py app.py
git commit -m "feat: main window + entry point — full app wired up"
```

---

## Task 13: Limpeza e ajustes finais

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Garantir que CLAUDE.md está atualizado na branch ui**

Adicionar ao final de `CLAUDE.md`:

```markdown
## Branch `ui` — App Desktop

- Entry point: `app.py`
- Rodar: `python app.py`
- Dependências novas: PyQt6
- SQLite gerado em `bot.db` automaticamente
- Histórico de exportações em `historico/`
```

- [ ] **Step 2: Verificar requirements.txt**

Confirmar que `PyQt6==6.7.0` está na lista. Caso contrário adicionar.

- [ ] **Step 3: Commit final**

```bash
git add CLAUDE.md requirements.txt
git commit -m "docs: update CLAUDE.md for ui branch"
```

---

## Notas de implementação

- **RAM:** Workers são QThreads (não processos), compartilham memória do processo principal. Com 3-5 workers simultâneos o consumo é baixo (~50-100MB total). Não há necessidade de multiprocessing.
- **Pausa suave:** O `QueueManager.pause()` bloqueia `next_cpf()` — cada worker termina o CPF atual antes de parar.
- **Histórico 7 dias:** `cleanup_old_exports()` roda no startup e remove arquivos + registros com mais de 7 dias.
- **Branch master intacta:** `main.py` e `export.py` originais não são tocados neste plano.
