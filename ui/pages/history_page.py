import os
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox
)
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
            has_file = bool(export_path and os.path.exists(str(export_path)))
            btn = QPushButton("Baixar" if has_file else "Sem exportação")
            btn.setEnabled(has_file)
            if has_file:
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
