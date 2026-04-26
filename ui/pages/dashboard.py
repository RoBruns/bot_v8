import os
import logging
import openpyxl
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QGridLayout, QFrame, QComboBox,
    QCheckBox, QMenu, QWidgetAction
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot
from core.api import TABELAS, ConsultStatus
from core.queue_manager import QueueManager
from core.worker import CpfWorker
from db import history_repo, users_repo
from db.database import init_db
import qtawesome as qta

HISTORICO_DIR = "historico"


def _metric_card(label: str, icon_name: str) -> tuple[QWidget, QLabel]:
    card = QFrame()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(20, 20, 20, 20)
    
    top_lay = QHBoxLayout()
    lbl_title = QLabel(label.upper())
    lbl_title.setObjectName("metricLabel")
    
    lbl_icon = QLabel()
    lbl_icon.setPixmap(qta.icon(icon_name, color='#3B82F6').pixmap(24, 24))
    
    top_lay.addWidget(lbl_title)
    top_lay.addStretch()
    top_lay.addWidget(lbl_icon)
    lay.addLayout(top_lay)
    
    val_lbl = QLabel("0")
    val_lbl.setObjectName("metricValue")
    lay.addWidget(val_lbl)
    return card, val_lbl


class DashboardPage(QWidget):
    export_completed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        init_db()
        self._workers: list[CpfWorker] = []
        self._queue: QueueManager | None = None
        self._base_id: int | None = None
        self._counters = {
            "processed": 0, "com_saldo": 0, "sem_saldo": 0,
            "nao_autorizado": 0, "cpf_invalido": 0, "falha_consulta": 0
        }
        self._workers_done = 0
        self._zerar_confirm = False
        self._build_ui()
        self.load_bases_combo()
        self.load_users_checkboxes()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        header.addWidget(title)
        
        # Selecionar Base
        header.addStretch()
        header.addWidget(QLabel("Base Ativa:"))
        self.combo_base = QComboBox()
        self.combo_base.setMinimumWidth(250)
        self.combo_base.currentIndexChanged.connect(self._on_base_selected)
        header.addWidget(self.combo_base)
        
        self.btn_reset = QPushButton(qta.icon('fa5s.redo', color='#EAB308'), " Zerar")
        self.btn_reset.setObjectName("btnSecondary")
        self.btn_reset.clicked.connect(self._reset_base)
        header.addWidget(self.btn_reset)

        self.btn_export = QPushButton(qta.icon('fa5s.file-excel', color='white'), " Exportar")
        self.btn_export.setObjectName("btnSecondary")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export)
        header.addWidget(self.btn_export)
        root.addLayout(header)

        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.hide()
        root.addWidget(self.lbl_feedback)

        control_card = QFrame()
        control_card.setObjectName("card")
        control_lay = QVBoxLayout(control_card)
        control_lay.setContentsMargins(24, 24, 24, 24)
        control_lay.setSpacing(16)

        # Seleção de usuários — botão dropdown com checkboxes
        users_row = QHBoxLayout()
        users_row.setSpacing(8)
        lbl_users = QLabel("Usuários:")
        lbl_users.setObjectName("metricLabel")
        users_row.addWidget(lbl_users)

        self._btn_users = QPushButton("Nenhum usuário")
        self._btn_users.setObjectName("btnSecondary")
        self._btn_users.setMinimumWidth(200)
        self._btn_users.clicked.connect(self._show_users_menu)
        users_row.addWidget(self._btn_users)
        users_row.addStretch()

        self._user_checkboxes: list[tuple[QCheckBox, int]] = []
        self._users_menu = QMenu(self)
        control_lay.addLayout(users_row)

        # Seleção de tabela
        tabela_row = QHBoxLayout()
        tabela_row.setSpacing(8)
        lbl_tabela = QLabel("Tabela:")
        lbl_tabela.setObjectName("metricLabel")
        tabela_row.addWidget(lbl_tabela)

        self.combo_tabela = QComboBox()
        for key, val in TABELAS.items():
            self.combo_tabela.addItem(val["nome"], val["id"])
        self.combo_tabela.setMinimumWidth(160)
        tabela_row.addWidget(self.combo_tabela)
        tabela_row.addStretch()
        control_lay.addLayout(tabela_row)

        status_row = QHBoxLayout()
        self.lbl_status = QLabel("Pronto para iniciar")
        self.lbl_status.setObjectName("statusStopped")
        self.lbl_status.setStyleSheet("font-size: 16px;")
        status_row.addWidget(self.lbl_status)
        status_row.addStretch()

        self.btn_start  = QPushButton(qta.icon('fa5s.play', color='white'), " Iniciar")
        self.btn_pause  = QPushButton(qta.icon('fa5s.pause', color='white'), " Pausar")
        self.btn_stop   = QPushButton(qta.icon('fa5s.stop', color='#EF4444'), " Parar")
        self.btn_stop.setObjectName("btnDanger")
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)

        self.btn_start.clicked.connect(self._start)
        self.btn_pause.clicked.connect(self._pause_resume)
        self.btn_stop.clicked.connect(self._stop)

        status_row.addWidget(self.btn_start)
        status_row.addWidget(self.btn_pause)
        status_row.addWidget(self.btn_stop)
        control_lay.addLayout(status_row)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        control_lay.addWidget(self.progress)
        root.addWidget(control_card)

        grid = QGridLayout()
        grid.setSpacing(16)
        cards_data = [
            ("Processados",    "processed",      "fa5s.layer-group"),
            ("Com Saldo",      "com_saldo",      "fa5s.check-circle"),
            ("Sem Saldo",      "sem_saldo",      "fa5s.times-circle"),
            ("Não Autorizado", "nao_autorizado", "fa5s.lock"),
            ("CPF Inválido",   "cpf_invalido",   "fa5s.exclamation-triangle"),
            ("Falha Consulta", "falha_consulta", "fa5s.server"),
        ]
        self._metric_labels: dict[str, QLabel] = {}
        for i, (label, key, icon) in enumerate(cards_data):
            card, val_lbl = _metric_card(label, icon)
            self._metric_labels[key] = val_lbl
            grid.addWidget(card, i // 3, i % 3)
        root.addLayout(grid)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["CPF", "RESULTADO", "MOTIVO"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        root.addWidget(self.table)

    def show_feedback(self, msg: str, is_error: bool = False, is_info: bool = False):
        if is_error:
            color, bg = "#EF4444", "#FEF2F2"
        elif is_info:
            color, bg = "#3B82F6", "#EFF6FF"
        else:
            color, bg = "#10B981", "#ECFDF5"
        self.lbl_feedback.setText(msg)
        self.lbl_feedback.setStyleSheet(f"color: {color}; background-color: {bg}; font-size: 14px; padding: 12px; border-radius: 8px; font-weight: bold;")
        self.lbl_feedback.show()

    def load_bases_combo(self):
        self.combo_base.blockSignals(True)
        self.combo_base.clear()
        bases = history_repo.get_recent_bases()
        for b in bases:
            self.combo_base.addItem(f"{b['filename']} ({b['total_cpfs']} CPFs)", b["id"])
        self.combo_base.blockSignals(False)
        if bases:
            self._on_base_selected()

    def load_users_checkboxes(self):
        self._users_menu.clear()
        self._user_checkboxes.clear()

        users = users_repo.list_users()
        for user in users:
            cb = QCheckBox(user["username"])
            cb.setChecked(True)
            cb.stateChanged.connect(self._update_users_btn_label)
            action = QWidgetAction(self._users_menu)
            action.setDefaultWidget(cb)
            self._users_menu.addAction(action)
            self._user_checkboxes.append((cb, user["id"]))

        self._update_users_btn_label()

    def _show_users_menu(self):
        pos = self._btn_users.mapToGlobal(self._btn_users.rect().bottomLeft())
        self._users_menu.exec(pos)

    def _update_users_btn_label(self):
        selected = [cb.text() for cb, _ in self._user_checkboxes if cb.isChecked()]
        if not selected:
            self._btn_users.setText("Nenhum selecionado")
        elif len(selected) == len(self._user_checkboxes):
            self._btn_users.setText(f"Todos ({len(selected)})")
        else:
            self._btn_users.setText(", ".join(selected))

    def _on_base_selected(self):
        base_id = self.combo_base.currentData()
        if not base_id:
            return
            
        self._base_id = base_id
        b = history_repo.get_base(base_id)
        if not b:
            return
            
        self._counters = {
            "processed": b["processed"],
            "com_saldo": b["com_saldo"],
            "sem_saldo": b["sem_saldo"],
            "nao_autorizado": b["nao_autorizado"],
            "cpf_invalido": b["cpf_invalido"],
            "falha_consulta": b["falha_consulta"]
        }
        
        for key, lbl in self._metric_labels.items():
            lbl.setText(str(self._counters[key]))
            
        self.progress.setMaximum(b["total_cpfs"])
        self.progress.setValue(self._counters["processed"])
        
        # Load previous results to table
        self.table.setRowCount(0)
        results = history_repo.get_base_results(base_id)
        # Mostrar os últimos 100 para não travar a UI se a base for gigante
        for r in results[-100:]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r["cpf"]))
            self.table.setItem(row, 1, QTableWidgetItem(r["valor"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(r["motivo"] or "")))
            
        if self._counters["processed"] >= b["total_cpfs"] and b["total_cpfs"] > 0:
            self.lbl_status.setText("Concluído")
            self.btn_start.setEnabled(False)
            self.btn_export.setEnabled(True)
        else:
            self.lbl_status.setText("Pronto para iniciar")
            self.btn_start.setEnabled(True)
            self.btn_export.setEnabled(True) if self._counters["processed"] > 0 else self.btn_export.setEnabled(False)

    def _reset_base(self):
        if not self._base_id:
            return

        if not self._zerar_confirm:
            self._zerar_confirm = True
            self.btn_reset.setText(" Tem certeza?")
            self.btn_reset.setStyleSheet("background-color: #EF4444; color: white;")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(3000, self._cancel_reset)
            return

        b = history_repo.get_base(self._base_id)
        logging.info(f"[dashboard] Base zerada: '{b['filename']}' (id={self._base_id})")
        history_repo.reset_base(self._base_id)
        self._on_base_selected()
        self._cancel_reset()
        self.show_feedback("Progresso zerado com sucesso!", is_info=True)

    def _cancel_reset(self):
        self._zerar_confirm = False
        self.btn_reset.setText(" Zerar")
        self.btn_reset.setStyleSheet("")

    def _start(self):
        self.lbl_feedback.hide()
        selected_ids = {uid for cb, uid in self._user_checkboxes if cb.isChecked()}
        users = [u for u in users_repo.list_users() if u["id"] in selected_ids]
        if not users:
            self.show_feedback("Atenção: Selecione ao menos um usuário V8 para iniciar.", is_error=True)
            return

        if not self._base_id:
            self.show_feedback("Atenção: Nenhuma base selecionada.", is_error=True)
            return

        b = history_repo.get_base(self._base_id)
        if not b:
            return

        try:
            wb = openpyxl.load_workbook(b["filepath"], data_only=True)
            sheet = wb.active
            all_cpfs = [str(r[0]) for r in sheet.iter_rows(min_row=2, max_col=1, values_only=True) if r[0]]
        except Exception as e:
            self.show_feedback(f"Erro ao abrir arquivo da base: {e}", is_error=True)
            logging.error(f"[dashboard] Erro ao abrir arquivo da base '{b['filename']}': {e}")
            return

        processed = history_repo.get_processed_cpfs(self._base_id)
        pending_cpfs = [cpf for cpf in all_cpfs if cpf not in processed]

        if not pending_cpfs:
            self.show_feedback("Aviso: Todos os CPFs dessa base já foram processados.", is_info=True)
            return

        fees_id = self.combo_tabela.currentData()
        tabela_nome = self.combo_tabela.currentText()
        usernames = [u["username"] for u in users]
        logging.info(
            f"[dashboard] Iniciando execução — Base: '{b['filename']}' | "
            f"Tabela: {tabela_nome} | CPFs pendentes: {len(pending_cpfs)} | "
            f"Usuários: {', '.join(usernames)}"
        )

        self._workers_done = 0
        self._queue = QueueManager(pending_cpfs)
        self._workers = []
        for user in users:
            creds = users_repo.get_user_credentials(user["id"])
            worker = CpfWorker(
                worker_id=user["id"],
                username=creds["username"],
                password=creds["password"],
                fees_id=fees_id,
                queue=self._queue,
                session_id=self._base_id,
            )
            worker.result_ready.connect(self._on_result)
            worker.finished_worker.connect(self._on_worker_done)
            self._workers.append(worker)

        for w in self._workers:
            w.start()

        self.btn_start.setEnabled(False)
        self.btn_reset.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.combo_base.setEnabled(False)
        self.combo_tabela.setEnabled(False)
        self._btn_users.setEnabled(False)
        self.lbl_status.setText("Rodando")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def _pause_resume(self):
        if self._queue is None:
            return
        if self._queue.is_paused:
            self._queue.resume()
            self.btn_pause.setText(" Pausar")
            self.btn_pause.setIcon(qta.icon('fa5s.pause', color='white'))
            self.lbl_status.setText("Rodando")
            self.lbl_status.setStyleSheet("color: #4CAF50; font-weight: bold;")
            logging.info("[dashboard] Execução retomada.")
        else:
            self._queue.pause()
            self.btn_pause.setText(" Retomar")
            self.btn_pause.setIcon(qta.icon('fa5s.play', color='white'))
            self.lbl_status.setText("Pausado")
            self.lbl_status.setStyleSheet("color: #EAB308; font-weight: bold;")
            logging.info("[dashboard] Execução pausada.")

    def _stop(self):
        if self._queue:
            self._queue.stop()
        logging.info("[dashboard] Parada solicitada pelo usuário.")
        self.lbl_status.setText("Parando...")
        self.lbl_status.setStyleSheet("color: #EF4444; font-weight: bold;")
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

        if self._base_id:
            history_repo.add_result(self._base_id, cpf, valor, str(motivo or ""))
            history_repo.update_base_counters(self._base_id, c)

        # Atualiza tabela limitando a 100 pra não pesar
        if self.table.rowCount() > 100:
            self.table.removeRow(0)
            
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
        c = self._counters
        logging.info(
            f"[dashboard] Execução concluída — "
            f"Processados: {c['processed']} | Com saldo: {c['com_saldo']} | "
            f"Sem saldo: {c['sem_saldo']} | Não autorizado: {c['nao_autorizado']} | "
            f"CPF inválido: {c['cpf_invalido']} | Falha: {c['falha_consulta']}"
        )
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_reset.setEnabled(True)
        self.btn_export.setEnabled(True)
        self.combo_base.setEnabled(True)
        self.combo_tabela.setEnabled(True)
        self._btn_users.setEnabled(True)
        self.btn_pause.setText(" Pausar")
        self.btn_pause.setIcon(qta.icon('fa5s.pause', color='white'))
        self.lbl_status.setText("Concluído")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-weight: bold;")

    def _export(self):
        if self._base_id is None:
            return
        from core.exporter import export_session
        os.makedirs(HISTORICO_DIR, exist_ok=True)
        
        b = history_repo.get_base(self._base_id)
        if not b: return
        
        results = history_repo.get_base_results(self._base_id)
        session_info = {
            "base_name": b["filename"],
            "tabela_simulacao": b["tabela_nome"],
            "processed": self._counters["processed"],
            "com_saldo": self._counters["com_saldo"],
            "sem_saldo": self._counters["sem_saldo"],
            "nao_autorizado": self._counters["nao_autorizado"],
            "cpf_invalido": self._counters["cpf_invalido"],
            "falha_consulta": self._counters["falha_consulta"],
        }
        filename = f"Saldos_{b['filename']}_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.xlsx"
        filepath = os.path.join(HISTORICO_DIR, filename)
        export_session(results, session_info, filepath)
        history_repo.add_export(self._base_id, filename, filepath)
        logging.info(f"[dashboard] Exportação gerada: {filepath}")
        self.export_completed.emit(filename)
        self.show_feedback(f"Exportado! Resultado salvo em: {filepath}", is_info=True)
