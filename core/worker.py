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
