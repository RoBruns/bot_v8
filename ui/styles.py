import qtawesome as qta
from PyQt6.QtGui import QIcon

PALETTES = {
    "dark": {
        "bg_main": "#0F172A",
        "bg_surface": "#1E293B",
        "border": "#334155",
        "text_primary": "#F8FAFC",
        "text_secondary": "#94A3B8",
        "primary": "#2563EB",
        "primary_hover": "#3B82F6",
        "primary_active": "#1D4ED8",
        "danger": "#EF4444",
        "danger_hover_bg": "rgba(239, 68, 68, 0.1)",
        "secondary_bg": "#334155",
        "secondary_hover": "#475569",
        "table_selected": "rgba(37, 99, 235, 0.15)",
        "menu_active_bg": "rgba(37, 99, 235, 0.15)",
        "menu_active_border": "#3B82F6",
        "menu_active_text": "#60A5FA",
        "scrollbar_bg": "#0F172A",
        "scrollbar_handle": "#475569",
        "scrollbar_hover": "#64748B",
    },
    "light": {
        "bg_main": "#F1F5F9",
        "bg_surface": "#FFFFFF",
        "border": "#E2E8F0",
        "text_primary": "#0F172A",
        "text_secondary": "#64748B",
        "primary": "#2563EB",
        "primary_hover": "#3B82F6",
        "primary_active": "#1D4ED8",
        "danger": "#EF4444",
        "danger_hover_bg": "rgba(239, 68, 68, 0.05)",
        "secondary_bg": "#E2E8F0",
        "secondary_hover": "#CBD5E1",
        "table_selected": "rgba(37, 99, 235, 0.08)",
        "menu_active_bg": "rgba(37, 99, 235, 0.1)",
        "menu_active_border": "#2563EB",
        "menu_active_text": "#1D4ED8",
        "scrollbar_bg": "#F1F5F9",
        "scrollbar_handle": "#CBD5E1",
        "scrollbar_hover": "#94A3B8",
    }
}

def get_stylesheet(theme: str) -> str:
    p = PALETTES.get(theme, PALETTES["dark"])
    return f"""
    /* ── Base ── */
    QWidget {{
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
        font-size: 14px;
        color: {p["text_primary"]};
    }}

    QMainWindow, #centralWidget, QStackedWidget > QWidget {{
        background-color: {p["bg_main"]};
    }}

    QLabel {{
        background: transparent;
    }}

    /* ── Sidebar ── */
    #sidebar {{
        background-color: {p["bg_surface"]};
        border-right: 1px solid {p["border"]};
    }}

    #sidebar QPushButton {{
        background-color: transparent;
        color: {p["text_secondary"]};
        border: none;
        text-align: left;
        padding: 12px 18px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
    }}

    #sidebar QPushButton:hover {{
        background-color: {p["secondary_bg"]};
        color: {p["text_primary"]};
    }}

    #sidebar QPushButton:checked {{
        background-color: {p["menu_active_bg"]};
        color: {p["menu_active_text"]};
        font-weight: bold;
        border-left: 4px solid {p["menu_active_border"]};
        border-top-left-radius: 0px;
        border-bottom-left-radius: 0px;
    }}

    /* ── Cards / Painéis ── */
    #card {{
        background-color: {p["bg_surface"]};
        border: 1px solid {p["border"]};
        border-radius: 12px;
    }}

    /* ── Botões de ação ── */
    QPushButton {{
        background-color: {p["primary"]};
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        font-size: 14px;
    }}

    QPushButton:hover {{
        background-color: {p["primary_hover"]};
    }}

    QPushButton:pressed {{
        background-color: {p["primary_active"]};
    }}

    QPushButton:disabled {{
        background-color: {p["secondary_bg"]};
        color: {p["text_secondary"]};
    }}

    QPushButton#btnDanger {{
        background-color: transparent;
        border: 1px solid {p["danger"]};
        color: {p["danger"]};
    }}

    QPushButton#btnDanger:hover {{
        background-color: {p["danger_hover_bg"]};
    }}

    QPushButton#btnSecondary {{
        background-color: {p["secondary_bg"]};
        color: {p["text_primary"]};
    }}

    QPushButton#btnSecondary:hover {{
        background-color: {p["secondary_hover"]};
    }}

    QPushButton#btnTheme {{
        background-color: transparent;
        color: {p["text_secondary"]};
        border: 1px solid {p["border"]};
    }}

    QPushButton#btnTheme:hover {{
        background-color: {p["secondary_bg"]};
        color: {p["text_primary"]};
    }}

    /* ── Inputs ── */
    QLineEdit, QComboBox {{
        background-color: {p["bg_main"]};
        color: {p["text_primary"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 14px;
    }}

    QLineEdit:focus, QComboBox:focus {{
        border: 1px solid {p["primary"]};
    }}

    QComboBox::drop-down {{ border: none; width: 30px; }}
    QComboBox::down-arrow {{ image: none; }}
    QComboBox QAbstractItemView {{
        background-color: {p["bg_surface"]};
        color: {p["text_primary"]};
        selection-background-color: {p["border"]};
        border: 1px solid {p["border"]};
        border-radius: 6px;
        outline: none;
    }}

    /* ── Tabelas ── */
    QTableWidget {{
        background-color: {p["bg_surface"]};
        color: {p["text_secondary"]};
        gridline-color: transparent;
        border: 1px solid {p["border"]};
        border-radius: 12px;
        outline: none;
    }}

    QTableWidget::item {{
        padding: 12px;
        border-bottom: 1px solid {p["border"]};
    }}

    QTableWidget::item:selected {{
        background-color: {p["table_selected"]};
        color: {p["text_primary"]};
    }}

    QHeaderView::section {{
        background-color: {p["bg_main"]};
        color: {p["text_secondary"]};
        padding: 12px;
        border: none;
        border-bottom: 2px solid {p["border"]};
        font-weight: 600;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* ── Scrollbar ── */
    QScrollBar:vertical {{
        background: {p["scrollbar_bg"]};
        width: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background: {p["scrollbar_handle"]};
        border-radius: 5px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{ background: {p["scrollbar_hover"]}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

    /* ── Labels de status ── */
    QLabel#statusRunning  {{ color: #22C55E; font-weight: bold; }}
    QLabel#statusPaused   {{ color: #EAB308; font-weight: bold; }}
    QLabel#statusStopped  {{ color: {p["text_secondary"]}; font-weight: bold; }}

    QLabel#metricValue {{
        color: {p["text_primary"]};
        font-size: 32px;
        font-weight: 800;
    }}

    QLabel#metricLabel {{
        color: {p["text_secondary"]};
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* ── Menu suspenso ── */
    QMenu {{
        background-color: {p["bg_surface"]};
        border: 1px solid {p["border"]};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu QCheckBox {{
        background-color: transparent;
        color: {p["text_primary"]};
        padding: 8px 12px;
        spacing: 8px;
        border-radius: 6px;
        min-width: 180px;
    }}

    QMenu QCheckBox:hover {{
        background-color: {p["secondary_bg"]};
    }}

    QMenu QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {p["border"]};
        border-radius: 4px;
        background-color: {p["bg_main"]};
    }}

    QMenu QCheckBox::indicator:checked {{
        background-color: {p["primary"]};
        border-color: {p["primary"]};
    }}

    /* ── ProgressBar ── */
    QProgressBar {{
        border: none;
        background-color: {p["secondary_bg"]};
        border-radius: 6px;
        text-align: center;
        color: transparent; 
        height: 12px;
    }}

    QProgressBar::chunk {{
        background-color: {p["primary"]};
        border-radius: 6px;
    }}
    """
