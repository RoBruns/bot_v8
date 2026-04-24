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

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet("""
            QProgressBar { border: 1px solid #4C4F54; border-radius: 5px; background: #2E3535; text-align: center; color: #EFDFC5; }
            QProgressBar::chunk { background-color: #8F0B13; border-radius: 4px; }
        """)
        root.addWidget(self.progress)

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
        os.makedirs(BASE_DIR, exist_ok=True)
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
        os.makedirs(BASE_DIR, exist_ok=True)
        base_filename = getattr(self, '_base_filename', os.listdir(BASE_DIR)[0] if os.listdir(BASE_DIR) else "base.xlsx")

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

        if self._session_id:
            history_repo.update_session_counters(self._session_id, {**c, "session_id": self._session_id})

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
            "tabela_simulacao": next(
                (t["nome"] for t in TABELAS.values() if t["id"] == getattr(self, '_tabela_id', '')), "-"
            ),
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
