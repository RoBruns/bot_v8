import os
import shutil
import openpyxl
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QComboBox,
    QScrollArea, QFrame, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from core.api import TABELAS
from db.history_repo import add_base, get_recent_bases, delete_base
import qtawesome as qta

BASE_DIR = "base"


class BaseCard(QFrame):
    deleted = pyqtSignal(int)

    def __init__(self, base: dict, parent=None):
        super().__init__(parent)
        self.base_id = base["id"]
        self._delete_confirm = False
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Linha topo: nome + tabela + data + botão excluir
        top = QHBoxLayout()
        top.setSpacing(12)

        lbl_name = QLabel(base["filename"])
        lbl_name.setStyleSheet("font-size: 14px; font-weight: 700;")
        lbl_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(lbl_name)

        lbl_tab = QLabel(f"Tabela: {base['tabela_nome']}")
        lbl_tab.setObjectName("metricLabel")
        top.addWidget(lbl_tab)

        lbl_date = QLabel(str(base.get("uploaded_at", ""))[:16])
        lbl_date.setObjectName("metricLabel")
        top.addWidget(lbl_date)

        self.btn_del = QPushButton(qta.icon('fa5s.trash-alt', color='#EF4444'), "")
        self.btn_del.setToolTip("Excluir Base")
        self.btn_del.setStyleSheet("background: transparent; border: none; padding: 4px;")
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.clicked.connect(self._on_delete)
        top.addWidget(self.btn_del)

        layout.addLayout(top)

        # Linha inferior: progresso
        processed = base.get("processed", 0)
        total = base.get("total_cpfs", 0)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(12)

        bar = QProgressBar()
        bar.setMaximum(max(total, 1))
        bar.setValue(processed)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        progress_row.addWidget(bar)

        pct = int(processed / total * 100) if total > 0 else 0
        lbl_progress = QLabel(f"{processed} / {total} CPFs ({pct}%)")
        lbl_progress.setObjectName("metricLabel")
        lbl_progress.setFixedWidth(180)
        lbl_progress.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(lbl_progress)

        layout.addLayout(progress_row)

    def _on_delete(self):
        if not self._delete_confirm:
            self._delete_confirm = True
            self.btn_del.setText(" Tem certeza?")
            self.btn_del.setStyleSheet("background-color: #EF4444; color: white; border-radius: 4px; padding: 4px 8px; font-weight: bold;")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(3000, self._cancel_delete)
            return

        delete_base(self.base_id)
        self.deleted.emit(self.base_id)

    def _cancel_delete(self):
        try:
            self._delete_confirm = False
            self.btn_del.setText("")
            self.btn_del.setStyleSheet("background: transparent; border: none; padding: 4px;")
        except RuntimeError:
            pass


class BasePage(QWidget):
    bases_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.load_bases()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        title = QLabel("Bases de Consulta")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        root.addWidget(title)

        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.hide()
        root.addWidget(self.lbl_feedback)

        # Controles de upload
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(12)

        ctrl_row.addWidget(QLabel("Tabela de simulação:"))
        self.combo_tabela = QComboBox()
        for key, val in TABELAS.items():
            self.combo_tabela.addItem(val["nome"], val["id"])
        ctrl_row.addWidget(self.combo_tabela)

        btn_select = QPushButton(qta.icon('fa5s.upload', color='white'), " Carregar Nova Base XLSX")
        btn_select.clicked.connect(self._select_file)
        ctrl_row.addWidget(btn_select)
        ctrl_row.addStretch()

        root.addLayout(ctrl_row)

        # Área de scroll com cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setStyleSheet("background: transparent;")

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_widget)
        root.addWidget(scroll)

    def load_bases(self):
        # Remove todos os cards existentes (exceto o stretch no final)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        bases = get_recent_bases(days=7)
        if not bases:
            lbl = QLabel("Nenhuma base adicionada nos últimos 7 dias.")
            lbl.setObjectName("metricLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cards_layout.insertWidget(0, lbl)
            return

        for b in bases:
            card = BaseCard(b)
            card.deleted.connect(self._on_deleted)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

    def _on_deleted(self, _base_id: int):
        self.show_feedback("Base e dados associados foram excluídos com sucesso!", is_info=True)
        self.load_bases()
        self.bases_changed.emit()

    def show_feedback(self, msg: str, is_error: bool = False, is_info: bool = False):
        if is_error:
            color, bg = "#EF4444", "#FEF2F2"
        elif is_info:
            color, bg = "#3B82F6", "#EFF6FF"
        else:
            color, bg = "#10B981", "#ECFDF5"
        self.lbl_feedback.setText(msg)
        self.lbl_feedback.setStyleSheet(
            f"color: {color}; background-color: {bg}; font-size: 14px; "
            f"padding: 12px; border-radius: 8px; font-weight: bold;"
        )
        self.lbl_feedback.show()

    def _select_file(self):
        self.lbl_feedback.hide()
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar base XLSX", "", "Excel Files (*.xlsx)"
        )
        if not path:
            return

        os.makedirs(BASE_DIR, exist_ok=True)

        try:
            wb = openpyxl.load_workbook(path, data_only=True)
            sheet = wb.active
            cpfs = [str(r[0]) for r in sheet.iter_rows(min_row=2, max_col=1, values_only=True) if r[0]]
            total_cpfs = len(cpfs)
        except Exception as e:
            self.show_feedback(f"Erro ao ler arquivo: {e}", is_error=True)
            return

        if total_cpfs == 0:
            self.show_feedback("Atenção: A base não possui CPFs válidos na primeira coluna.", is_error=True)
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = f"{timestamp}_{os.path.basename(path)}"
        dest = os.path.join(BASE_DIR, new_filename)
        shutil.copy2(path, dest)

        tabela_id = self.combo_tabela.currentData()
        tabela_nome = self.combo_tabela.currentText()

        add_base(os.path.basename(path), dest, tabela_id, tabela_nome, total_cpfs)

        self.load_bases()
        self.bases_changed.emit()
        self.show_feedback(f"Sucesso! Base '{os.path.basename(path)}' adicionada com {total_cpfs} CPFs.")
