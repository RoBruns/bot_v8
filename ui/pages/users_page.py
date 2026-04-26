from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox,
    QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from db import users_repo
import qtawesome as qta


class UserCard(QFrame):
    def __init__(self, user: dict, on_remove, parent=None):
        super().__init__(parent)
        self.user_id = user["id"]
        self.on_remove = on_remove
        self._delete_confirm = False
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(qta.icon('fa5s.user', color='#3B82F6').pixmap(24, 24))
        layout.addWidget(icon_lbl)

        lbl_name = QLabel(user["username"])
        lbl_name.setStyleSheet("font-size: 14px; font-weight: 700;")
        lbl_name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(lbl_name)

        lbl_id = QLabel(f"ID: {user['id']}")
        lbl_id.setObjectName("metricLabel")
        layout.addWidget(lbl_id)

        self.btn_del = QPushButton(qta.icon('fa5s.trash-alt', color='#EF4444'), "")
        self.btn_del.setToolTip("Remover usuário")
        self.btn_del.setStyleSheet("background: transparent; border: none; padding: 4px;")
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.clicked.connect(self._on_delete)
        layout.addWidget(self.btn_del)

    def _on_delete(self):
        if not self._delete_confirm:
            self._delete_confirm = True
            self.btn_del.setText(" Tem certeza?")
            self.btn_del.setStyleSheet("background-color: #EF4444; color: white; border-radius: 4px; padding: 4px 8px; font-weight: bold;")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(3000, self._cancel_delete)
            return
            
        self.on_remove(self.user_id)

    def _cancel_delete(self):
        try:
            self._delete_confirm = False
            self.btn_del.setText("")
            self.btn_del.setStyleSheet("background: transparent; border: none; padding: 4px;")
        except RuntimeError:
            pass


class UsersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.load_users()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        title = QLabel("Usuários V8")
        title.setStyleSheet("font-size: 28px; font-weight: 800;")
        root.addWidget(title)

        self.lbl_feedback = QLabel("")
        self.lbl_feedback.setWordWrap(True)
        self.lbl_feedback.hide()
        root.addWidget(self.lbl_feedback)

        # Formulário de adição
        form = QHBoxLayout()
        form.setSpacing(12)

        self.input_user = QLineEdit()
        self.input_user.setPlaceholderText("Usuário V8")
        self.input_pass = QLineEdit()
        self.input_pass.setPlaceholderText("Senha V8")
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pass.returnPressed.connect(self._add_user)

        btn_add = QPushButton(qta.icon('fa5s.plus', color='white'), " Adicionar")
        btn_add.clicked.connect(self._add_user)

        form.addWidget(self.input_user)
        form.addWidget(self.input_pass)
        form.addWidget(btn_add)
        form.addStretch()
        root.addLayout(form)

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

    def load_users(self):
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        users = users_repo.list_users()
        if not users:
            lbl = QLabel("Nenhum usuário cadastrado.")
            lbl.setObjectName("metricLabel")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cards_layout.insertWidget(0, lbl)
            return

        for user in users:
            card = UserCard(user, on_remove=self._remove_user)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

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

    def _add_user(self):
        username = self.input_user.text().strip()
        password = self.input_pass.text().strip()
        if not username or not password:
            self.show_feedback("Preencha usuário e senha.", is_error=True)
            return

        from PyQt6.QtWidgets import QApplication
        from core.api import get_token
        
        self.show_feedback("Autenticando na V8...", is_info=True)
        QApplication.processEvents()

        token = get_token(username, password)
        if not token:
            self.show_feedback("Falha na autenticação. Verifique suas credenciais.", is_error=True)
            return

        try:
            users_repo.add_user(username, password)
            self.input_user.clear()
            self.input_pass.clear()
            self.load_users()
            self.show_feedback(f"Usuário '{username}' autenticado e adicionado com sucesso!")
        except Exception as e:
            self.show_feedback(f"Erro ao salvar usuário (provavelmente já existe).", is_error=True)

    def _remove_user(self, user_id: int):
        users_repo.remove_user(user_id)
        self.load_users()
        self.show_feedback("Usuário removido com sucesso.", is_info=True)
