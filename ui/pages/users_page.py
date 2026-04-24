from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox
)
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
