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

        self.lbl_current = QLabel("Nenhuma base carregada")
        self.lbl_current.setStyleSheet("color: #4C4F54; font-size: 12px;")
        root.addWidget(self.lbl_current)

        btn_row = QHBoxLayout()
        btn_select = QPushButton("Selecionar arquivo XLSX")
        btn_select.clicked.connect(self._select_file)
        btn_row.addWidget(btn_select)
        btn_row.addStretch()
        root.addLayout(btn_row)

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
