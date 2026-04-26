from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout
from PyQt6.QtCore import QSettings, QTimer
from ui.widgets.animated_stack import AnimatedStackedWidget
from ui.widgets.sidebar import Sidebar
from ui.widgets.onboarding_overlay import OnboardingOverlay
from ui.pages.dashboard import DashboardPage
from ui.pages.users_page import UsersPage
from ui.pages.base_page import BasePage
from ui.pages.history_page import HistoryPage
from ui.styles import get_stylesheet
from db.database import get_setting, set_setting


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BOT FGTS")
        self.setMinimumSize(1000, 660)
        
        self.settings = QSettings("V8", "BotFGTS")
        self.current_theme = self.settings.value("theme", "dark")
        self.setStyleSheet(get_stylesheet(self.current_theme))

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar(current_theme=self.current_theme)
        self.sidebar.page_changed.connect(self._switch_page)
        self.sidebar.theme_toggled.connect(self._change_theme)
        layout.addWidget(self.sidebar)

        self.stack = AnimatedStackedWidget()
        layout.addWidget(self.stack)

        self.dashboard    = DashboardPage()
        self.users_page   = UsersPage()
        self.base_page    = BasePage()
        self.history_page = HistoryPage()

        self.stack.addWidget(self.dashboard)     # index 0
        self.stack.addWidget(self.users_page)    # index 1
        self.stack.addWidget(self.base_page)     # index 2
        self.stack.addWidget(self.history_page)  # index 3

        self.base_page.bases_changed.connect(self.dashboard.load_bases_combo)
        self.base_page.bases_changed.connect(self.history_page.load_history)
        self.dashboard.export_completed.connect(self._on_export_completed)

        self._pages = {
            "dashboard": 0,
            "users":     1,
            "base":      2,
            "history":   3,
        }

        self.sidebar.help_requested.connect(self._open_onboarding)
        self._onboarding: OnboardingOverlay | None = None
        QTimer.singleShot(200, self._maybe_show_onboarding)

    def _switch_page(self, key: str):
        idx = self._pages.get(key, 0)
        self.stack.setCurrentIndex(idx)
        if key == "history":
            self.history_page.load_history()
        elif key == "base":
            self.base_page.load_bases()
        elif key == "dashboard":
            self.dashboard.load_users_checkboxes()

    def _change_theme(self, new_theme: str):
        self.current_theme = new_theme
        self.settings.setValue("theme", new_theme)
        self.setStyleSheet(get_stylesheet(self.current_theme))

    def _on_export_completed(self, filename: str):
        self.sidebar._on_nav("history")
        self.history_page.load_history(highlight_filename=filename)

    def _maybe_show_onboarding(self):
        if get_setting("onboarding_done") != "1":
            self._open_onboarding()

    def _open_onboarding(self):
        if self._onboarding is not None:
            self._onboarding.deleteLater()
        self._onboarding = OnboardingOverlay(self)
        self._onboarding.finished.connect(self._on_onboarding_finished)
        self._onboarding.show()
        self._onboarding.raise_()

    def _on_onboarding_finished(self):
        set_setting("onboarding_done", "1")

    def resizeEvent(self, event):
        if self._onboarding is not None and self._onboarding.isVisible():
            self._onboarding.setGeometry(self.rect())
        super().resizeEvent(event)
