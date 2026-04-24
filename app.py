import sys
from PyQt6.QtWidgets import QApplication
from db.database import init_db
from db.history_repo import cleanup_old_exports
from ui.main_window import MainWindow


def main():
    init_db()
    cleanup_old_exports(days=7)
    app = QApplication(sys.argv)
    app.setApplicationName("BOT FGTS")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
