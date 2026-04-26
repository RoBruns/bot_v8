import os
import shutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from db import history_repo
import qtawesome as qta


class ExportCard(QFrame):
    def __init__(self, export: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.filename = str(export.get("filename", ""))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Linha topo: arquivo + botão baixar
        top = QHBoxLayout()
        top.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon('fa5s.file-excel', color='#22C55E').pixmap(24, 24))
        top.addWidget(icon_lbl)

        lbl_name = QLabel(str(export.get("filename", "")))
        lbl_name.setStyleSheet("font-size: 14px; font-weight: 700;")
        lbl_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top.addWidget(lbl_name)

        filepath = export.get("filepath")
        has_file = bool(filepath and os.path.exists(str(filepath)))
        if has_file:
            self.btn_dl = QPushButton(qta.icon('fa5s.download', color='white'), " Baixar")
            self.btn_dl.clicked.connect(lambda: self._download(filepath))
            self.btn_dl.setStyleSheet("""
                QPushButton {
                    background-color: #22C55E;
                    color: white;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #16A34A;
                }
            """)
        else:
            self.btn_dl = QPushButton("Não Encontrado")
            self.btn_dl.setEnabled(False)
        self.btn_dl.setFixedWidth(160)
        top.addWidget(self.btn_dl)

        layout.addLayout(top)

        # Linha inferior: metadados
        meta = QHBoxLayout()
        meta.setSpacing(24)

        def _tag(icon_name, text, color='#94A3B8'):
            row = QHBoxLayout()
            row.setSpacing(6)
            ico = QLabel()
            ico.setPixmap(qta.icon(icon_name, color=color).pixmap(14, 14))
            lbl = QLabel(text)
            lbl.setObjectName("metricLabel")
            row.addWidget(ico)
            row.addWidget(lbl)
            w = QWidget()
            w.setLayout(row)
            w.setStyleSheet("background: transparent;")
            return w

        meta.addWidget(_tag('fa5s.database', str(export.get("base_name", ""))))
        meta.addWidget(_tag('fa5s.table', str(export.get("tabela_nome", ""))))
        meta.addWidget(_tag('fa5s.users', f"Total: {export.get('total_cpfs', 0)}"))
        meta.addWidget(_tag('fa5s.check-circle', f"Com saldo: {export.get('com_saldo', 0)}", '#22C55E'))
        meta.addWidget(_tag('fa5s.times-circle', f"Sem saldo: {export.get('sem_saldo', 0)}", '#EF4444'))
        meta.addStretch()

        lbl_date = QLabel(str(export.get("exported_at", ""))[:16])
        lbl_date.setObjectName("metricLabel")
        meta.addWidget(lbl_date)

        layout.addLayout(meta)

    def _download(self, filepath: str):
        dest_dir = QFileDialog.getExistingDirectory(self, "Escolha a pasta de destino")
        if not dest_dir:
            return
        dest = os.path.join(dest_dir, os.path.basename(filepath))
        try:
            shutil.copy2(filepath, dest)
            self.btn_dl.setText(" Salvo!")
            self.btn_dl.setIcon(qta.icon('fa5s.check', color='white'))
        except Exception as e:
            self.btn_dl.setText(" Erro!")
            self.btn_dl.setIcon(qta.icon('fa5s.times', color='white'))
            
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, self._reset_btn_dl)

    def _reset_btn_dl(self):
        try:
            self.btn_dl.setText(" Baixar")
            self.btn_dl.setIcon(qta.icon('fa5s.download', color='white'))
        except RuntimeError:
            pass

    def play_glow_animation(self):
        self._glow_count = 0
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._toggle_glow)
        self._glow_timer.start(300)

    def _toggle_glow(self):
        self._glow_count += 1
        if self._glow_count % 2 == 1:
            self.setStyleSheet("#card { border: 2px solid #3B82F6; background-color: rgba(59, 130, 246, 0.1); }")
        else:
            self.setStyleSheet("")
            
        if self._glow_count >= 6:
            self._glow_timer.stop()
            self.setStyleSheet("")


class HistoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.load_history()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        header = QHBoxLayout()
        title = QLabel("Histórico de Exportações (últimos 7 dias)")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        btn_refresh = QPushButton(qta.icon('fa5s.sync-alt', color='white'), " Atualizar")
        btn_refresh.clicked.connect(self.load_history)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(btn_refresh)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.scroll.viewport().setStyleSheet("background: transparent;")

        self._cards_widget = QWidget()
        self._cards_widget.setStyleSheet("background: transparent;")
        self._cards_layout = QVBoxLayout(self._cards_widget)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch()

        self.scroll.setWidget(self._cards_widget)
        root.addWidget(self.scroll)

    def load_history(self, highlight_filename: str = None):
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        exports = history_repo.get_recent_exports(days=7)

        if not exports:
            lbl = QLabel("Nenhuma exportação nos últimos 7 dias.")
            lbl.setObjectName("metricLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cards_layout.insertWidget(0, lbl)
            return

        for e in exports:
            card = ExportCard(e)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

        if highlight_filename:
            QTimer.singleShot(100, lambda: self._highlight_card(highlight_filename))

    def _highlight_card(self, filename: str):
        for i in range(self._cards_layout.count() - 1):
            item = self._cards_layout.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if isinstance(card, ExportCard) and card.filename == filename:
                    self.scroll.ensureWidgetVisible(card)
                    card.play_glow_animation()
                    break
