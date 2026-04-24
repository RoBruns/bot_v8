from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QStackedWidget
from ui.widgets.sidebar import Sidebar
from ui.pages.dashboard import DashboardPage
from ui.pages.users_page import UsersPage
from ui.pages.base_page import BasePage
from ui.pages.history_page import HistoryPage
from ui.styles import STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BOT FGTS")
        self.setMinimumSize(1000, 660)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._switch_page)
        layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self.dashboard    = DashboardPage()
        self.users_page   = UsersPage()
        self.base_page    = BasePage()
        self.history_page = HistoryPage()

        self.stack.addWidget(self.dashboard)     # index 0
        self.stack.addWidget(self.users_page)    # index 1
        self.stack.addWidget(self.base_page)     # index 2
        self.stack.addWidget(self.history_page)  # index 3

        self.base_page.base_configured.connect(self.dashboard.set_base_config)

        self._pages = {
            "dashboard": 0,
            "users":     1,
            "base":      2,
            "history":   3,
        }

    def _switch_page(self, key: str):
        idx = self._pages.get(key, 0)
        self.stack.setCurrentIndex(idx)
        if key == "history":
            self.history_page.load_history()
