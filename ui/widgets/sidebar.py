from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, pyqtSignal, QSize
import qtawesome as qta
from ui.styles import PALETTES


SIDEBAR_COLLAPSED = 60
SIDEBAR_EXPANDED  = 220

NAV_ITEMS = [
    ("dashboard", "Dashboard", "fa5s.chart-pie"),
    ("users",     "Usuários",  "fa5s.users"),
    ("base",      "Base",      "fa5s.database"),
    ("history",   "Histórico", "fa5s.history"),
]


class Sidebar(QWidget):
    page_changed = pyqtSignal(str)
    theme_toggled = pyqtSignal(str)
    help_requested = pyqtSignal()

    def __init__(self, current_theme="dark", parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_COLLAPSED)
        self._expanded = False
        self.current_theme = current_theme
        self._buttons: dict[str, QPushButton] = {}

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 20, 8, 20)
        self.layout.setSpacing(8)

        for key, label, icon_name in NAV_ITEMS:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setIconSize(QSize(20, 20))
            btn.setToolTip(label)
            btn.clicked.connect(lambda checked, k=key: self._on_nav(k))
            self._buttons[key] = btn
            self.layout.addWidget(btn)

        self.layout.addStretch()
        
        self.btn_help = QPushButton()
        self.btn_help.setObjectName("btnTheme")
        self.btn_help.setIconSize(QSize(20, 20))
        self.btn_help.setToolTip("Ver tutorial")
        self.btn_help.clicked.connect(self.help_requested.emit)
        self.layout.addWidget(self.btn_help)

        self.btn_theme = QPushButton()
        self.btn_theme.setObjectName("btnTheme")
        self.btn_theme.setIconSize(QSize(20, 20))
        self.btn_theme.clicked.connect(self._on_theme_toggle)
        self.layout.addWidget(self.btn_theme)

        self.update_icons()
        self._buttons["dashboard"].setChecked(True)

    def update_icons(self):
        p = PALETTES.get(self.current_theme, PALETTES["dark"])
        for key, label, icon_name in NAV_ITEMS:
            icon = qta.icon(icon_name, color=p["text_secondary"], color_active=p["menu_active_text"])
            self._buttons[key].setIcon(icon)

        self.btn_help.setIcon(qta.icon("fa5s.question-circle", color=p["text_secondary"]))
        self.btn_help.setText("  Tutorial" if self._expanded else "")

        if self.current_theme == "dark":
            self.btn_theme.setIcon(qta.icon("fa5s.sun", color=p["text_secondary"]))
            self.btn_theme.setText("  Modo Claro" if self._expanded else "")
            self.btn_theme.setToolTip("Modo Claro")
        else:
            self.btn_theme.setIcon(qta.icon("fa5s.moon", color=p["text_secondary"]))
            self.btn_theme.setText("  Modo Escuro" if self._expanded else "")
            self.btn_theme.setToolTip("Modo Escuro")

    def _on_theme_toggle(self):
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.update_icons()
        self.theme_toggled.emit(self.current_theme)

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
        self.update_icons()

    def collapse(self):
        if not self._expanded:
            return
        self._expanded = False
        self._animate(SIDEBAR_COLLAPSED)
        for key, _, _ in NAV_ITEMS:
            self._buttons[key].setText("")
        self.update_icons()


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
