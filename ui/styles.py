# Paleta: #380F17 vinho | #8F0B13 vermelho | #EFDFC5 creme | #252B2B chumbo | #4C4F54 cinza

STYLESHEET = """
/* ── Base ── */
QWidget {
    background-color: #252B2B;
    color: #EFDFC5;
    font-family: 'Segoe UI';
    font-size: 13px;
}

QMainWindow {
    background-color: #252B2B;
}

/* ── Sidebar ── */
#sidebar {
    background-color: #380F17;
    border-right: 1px solid #4C4F54;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #EFDFC5;
    border: none;
    text-align: left;
    padding: 12px 16px;
    border-radius: 6px;
    font-size: 13px;
}

#sidebar QPushButton:hover {
    background-color: #8F0B13;
}

#sidebar QPushButton:checked {
    background-color: #8F0B13;
    font-weight: bold;
}

/* ── Cards / Painéis ── */
#card {
    background-color: #2E3535;
    border: 1px solid #4C4F54;
    border-radius: 8px;
    padding: 12px;
}

/* ── Botões de ação ── */
QPushButton {
    background-color: #8F0B13;
    color: #EFDFC5;
    border: none;
    border-radius: 6px;
    padding: 8px 18px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #B01020;
}

QPushButton:disabled {
    background-color: #4C4F54;
    color: #888;
}

QPushButton#btnDanger {
    background-color: #380F17;
    border: 1px solid #8F0B13;
}

QPushButton#btnDanger:hover {
    background-color: #8F0B13;
}

/* ── Inputs ── */
QLineEdit {
    background-color: #2E3535;
    color: #EFDFC5;
    border: 1px solid #4C4F54;
    border-radius: 5px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border: 1px solid #8F0B13;
}

/* ── Tabelas ── */
QTableWidget {
    background-color: #252B2B;
    gridline-color: #4C4F54;
    border: none;
}

QTableWidget::item {
    padding: 6px;
}

QTableWidget::item:selected {
    background-color: #8F0B13;
    color: #EFDFC5;
}

QHeaderView::section {
    background-color: #380F17;
    color: #EFDFC5;
    padding: 6px;
    border: none;
    font-weight: bold;
}

/* ── Scrollbar ── */
QScrollBar:vertical {
    background: #252B2B;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #4C4F54;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #8F0B13;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── ComboBox ── */
QComboBox {
    background-color: #2E3535;
    color: #EFDFC5;
    border: 1px solid #4C4F54;
    border-radius: 5px;
    padding: 5px 10px;
}

QComboBox::drop-down {
    border: none;
}

QComboBox QAbstractItemView {
    background-color: #2E3535;
    color: #EFDFC5;
    selection-background-color: #8F0B13;
}

/* ── Labels de status ── */
QLabel#statusRunning  { color: #4CAF50; font-weight: bold; }
QLabel#statusPaused   { color: #FFC107; font-weight: bold; }
QLabel#statusStopped  { color: #8F0B13; font-weight: bold; }
QLabel#metricValue    { color: #EFDFC5; font-size: 22px; font-weight: bold; }
QLabel#metricLabel    { color: #4C4F54; font-size: 11px; }
"""
