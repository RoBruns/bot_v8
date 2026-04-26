import logging
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal
from core.api import (
    ConsultStatus, create_session, get_token, process_cpf
)
from core.queue_manager import QueueManager
from db import history_repo


class CpfWorker(QThread):
    result_ready = pyqtSignal(str, str, object)   # cpf, valor_str, motivo
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
        log = logging.getLogger(f"worker.{self.username}")
        log.info(f"[{self.username}] Iniciando — obtendo token...")

        token = get_token(self.username, self.password)
        if not token:
            log.error(f"[{self.username}] Falha ao obter token. Worker encerrado.")
            self.finished_worker.emit(self.worker_id)
            return

        log.info(f"[{self.username}] Token obtido com sucesso.")
        http_session = create_session()
        processed = 0

        while True:
            cpf = self.queue.next_cpf()
            if cpf is None:
                break

            log.info(f"[{self.username}] Consultando CPF: {cpf}")
            cpf_str, result, reason = process_cpf(cpf, token, http_session, self.fees_id)

            if result == ConsultStatus.TOKEN_EXPIRADO:
                log.warning(f"[{self.username}] Token expirado. Renovando...")
                token = get_token(self.username, self.password)
                if not token:
                    log.error(f"[{self.username}] Falha ao renovar token. Worker encerrado.")
                    break
                log.info(f"[{self.username}] Token renovado com sucesso.")
                self.token_renewed.emit(self.worker_id)
                cpf_str, result, reason = process_cpf(cpf, token, http_session, self.fees_id)

            valor_str = str(result) if not isinstance(result, float) else f"{result:.2f}"

            if isinstance(result, float):
                log.info(f"[{self.username}] CPF {cpf_str} → COM SALDO: R$ {valor_str}")
            else:
                log.info(f"[{self.username}] CPF {cpf_str} → {valor_str}" + (f" ({reason})" if reason else ""))

            history_repo.add_result(self.session_id, cpf_str, valor_str, reason)
            self.result_ready.emit(cpf_str, valor_str, reason)
            processed += 1

        log.info(f"[{self.username}] Worker finalizado. CPFs processados nesta sessão: {processed}")
        self.finished_worker.emit(self.worker_id)
