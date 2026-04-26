import sys
import logging
from PyQt6.QtWidgets import QApplication
from db.database import init_db
from db.history_repo import cleanup_old_bases
from logger_setup import setup_logger
from ui.main_window import MainWindow


def main():
    setup_logger()
    logging.info("=== BOT FGTS iniciado ===")
    init_db()
    cleanup_old_bases(days=7)
    logging.info("Banco de dados inicializado. Bases antigas removidas.")
    app = QApplication(sys.argv)
    app.setApplicationName("BOT FGTS")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
