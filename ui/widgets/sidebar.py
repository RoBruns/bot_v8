from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtSignal, QSize
from PyQt6.QtGui import QIcon


SIDEBAR_COLLAPSED = 56
SIDEBAR_EXPANDED  = 200

NAV_ITEMS = [
    ("dashboard", "Dashboard", "assets/icons/dashboard.png"),
    ("users",     "Usuários",  "assets/icons/users.png"),
    ("base",      "Base",      "assets/icons/base.png"),
    ("history",   "Histórico", "assets/icons/history.png"),
]


class Sidebar(QWidget):
    page_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_COLLAPSED)
        self._expanded = False
        self._buttons: dict[str, QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(4)

        for key, label, icon_path in NAV_ITEMS:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setIcon(QIcon(icon_path))
            btn.setIconSize(QSize(22, 22))
            btn.setToolTip(label)
            btn.clicked.connect(lambda checked, k=key: self._on_nav(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()
        self._buttons["dashboard"].setChecked(True)

    def _on_nav(self, key: str):
        for k, btn in self._buttons.items():
            btn.setChecked(k == key)
        self.page_changed.emit(key)

    def expand(self):
        if self._expanded:
            return
        self._expanded = True
        self._animate(SIDEBAR_EXPANDED)
        for key, label, _ in NAV_ITEMS:
            self._buttons[key].setText(f"  {label}")

    def collapse(self):
        if not self._expanded:
            return
        self._expanded = False
        self._animate(SIDEBAR_COLLAPSED)
        for key, _, _ in NAV_ITEMS:
            self._buttons[key].setText("")

    def _animate(self, target_width: int):
        anim = QPropertyAnimation(self, b"minimumWidth", self)
        anim.setDuration(180)
        anim.setEndValue(target_width)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim2 = QPropertyAnimation(self, b"maximumWidth", self)
        anim2.setDuration(180)
        anim2.setEndValue(target_width)
        anim2.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        anim2.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def enterEvent(self, event):
        self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.collapse()
        super().leaveEvent(event)
