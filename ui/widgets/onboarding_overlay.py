from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPainter, QColor, QFont
import qtawesome as qta

STEPS = [
    {
        "icon": "fa5s.robot",
        "icon_color": "#3B82F6",
        "title": "Bem-vindo ao BOT FGTS",
        "body": (
            "Este app automatiza a consulta de saldo FGTS em massa.\n\n"
            "Ele lê uma planilha XLSX com CPFs, consulta cada um na API V8 "
            "e salva os resultados prontos para exportação em Excel.\n\n"
            "Siga os próximos passos para configurar tudo em minutos."
        ),
    },
    {
        "icon": "fa5s.users",
        "icon_color": "#8B5CF6",
        "title": "Usuários V8",
        "body": (
            "Na seção Usuários você cadastra as credenciais da API V8.\n\n"
            "Cada usuário vira um worker paralelo — quanto mais usuários ativos, "
            "mais CPFs são processados simultaneamente.\n\n"
            "Acesse pelo menu lateral > Usuários e clique em Adicionar."
        ),
    },
    {
        "icon": "fa5s.database",
        "icon_color": "#10B981",
        "title": "Bases de Consulta",
        "body": (
            "Na seção Base você carrega a planilha XLSX com os CPFs.\n\n"
            "O arquivo deve ter os CPFs na primeira coluna, a partir da linha 2 "
            "(linha 1 é o cabeçalho). Você também escolhe a tabela de simulação "
            "usada para calcular os saldos.\n\n"
            "O app guarda o progresso — se pausar no meio, continua de onde parou."
        ),
    },
    {
        "icon": "fa5s.chart-pie",
        "icon_color": "#F59E0B",
        "title": "Dashboard",
        "body": (
            "O Dashboard é o centro de controle da execução.\n\n"
            "Selecione a base, os usuários e a tabela de simulação, depois clique "
            "em Iniciar. Você pode Pausar e Retomar a qualquer momento. "
            "O botão Parar encerra a sessão atual sem perder o progresso já salvo."
        ),
    },
    {
        "icon": "fa5s.layer-group",
        "icon_color": "#EF4444",
        "title": "Métricas em Tempo Real",
        "body": (
            "Durante a execução, seis cards mostram o status de cada CPF:\n\n"
            "• Com Saldo — saldo disponível encontrado\n"
            "• Sem Saldo — saldo zerado ou parcelas abaixo de R$ 10\n"
            "• Não Autorizado — CPF sem autorização na instituição\n"
            "• CPF Inválido — rejeitado pela API\n"
            "• Falha Consulta — erro de rede ou resposta inesperada\n"
            "• Processados — total consultado até o momento"
        ),
    },
    {
        "icon": "fa5s.file-excel",
        "icon_color": "#10B981",
        "title": "Exportar Resultado",
        "body": (
            "Ao concluir (ou a qualquer momento com progresso parcial), "
            "clique em Exportar no Dashboard.\n\n"
            "O app gera um arquivo Excel com todos os resultados organizados "
            "e o salva na pasta historico/. O nome inclui a data e hora "
            "para facilitar a identificação."
        ),
    },
    {
        "icon": "fa5s.history",
        "icon_color": "#3B82F6",
        "title": "Histórico de Exportações",
        "body": (
            "Na seção Histórico você encontra todos os arquivos exportados.\n\n"
            "Clique em qualquer exportação para abrir a pasta onde o arquivo "
            "está salvo.\n\n"
            "Você pode revisitar este tutorial a qualquer momento pelo botão "
            "? no rodapé do menu lateral. Bom trabalho!"
        ),
    },
]


class OnboardingOverlay(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setGeometry(parent.rect())
        self._step = 0
        self._build_ui()
        self._update_step()

    def resizeEvent(self, event):
        self.setGeometry(self.parent().rect())
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 180))

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._card = QFrame()
        self._card.setObjectName("onboardingCard")
        self._card.setFixedWidth(560)
        self._card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self._card.setStyleSheet("""
            #onboardingCard {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 16px;
            }
        """)

        card_lay = QVBoxLayout(self._card)
        card_lay.setContentsMargins(40, 36, 40, 36)
        card_lay.setSpacing(20)

        # Ícone
        self._icon_lbl = QLabel()
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_lay.addWidget(self._icon_lbl)

        # Título
        self._title_lbl = QLabel()
        self._title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_lbl.setWordWrap(True)
        font = QFont()
        font.setPointSize(17)
        font.setBold(True)
        self._title_lbl.setFont(font)
        self._title_lbl.setStyleSheet("color: #F8FAFC;")
        card_lay.addWidget(self._title_lbl)

        # Corpo
        self._body_lbl = QLabel()
        self._body_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._body_lbl.setWordWrap(True)
        self._body_lbl.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.6;")
        card_lay.addWidget(self._body_lbl)

        # Bolinhas de progresso
        dots_row = QHBoxLayout()
        dots_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dots_row.setSpacing(8)
        self._dots: list[QLabel] = []
        for _ in STEPS:
            dot = QLabel("●")
            dot.setStyleSheet("color: #334155; font-size: 10px;")
            dots_row.addWidget(dot)
            self._dots.append(dot)
        card_lay.addLayout(dots_row)

        # Botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._btn_prev = QPushButton("Anterior")
        self._btn_prev.setObjectName("btnSecondary")
        self._btn_prev.clicked.connect(self._prev)
        btn_row.addWidget(self._btn_prev)

        btn_row.addStretch()

        self._btn_skip = QPushButton("Pular tutorial")
        self._btn_skip.setObjectName("btnSecondary")
        self._btn_skip.setStyleSheet("color: #64748B;")
        self._btn_skip.clicked.connect(self._finish)
        btn_row.addWidget(self._btn_skip)

        self._btn_next = QPushButton("Próximo")
        self._btn_next.clicked.connect(self._next)
        btn_row.addWidget(self._btn_next)

        card_lay.addLayout(btn_row)
        outer.addWidget(self._card)

    def _update_step(self):
        step = STEPS[self._step]
        total = len(STEPS)

        icon = qta.icon(step["icon"], color=step["icon_color"])
        self._icon_lbl.setPixmap(icon.pixmap(56, 56))
        self._title_lbl.setText(step["title"])
        self._body_lbl.setText(step["body"])

        for i, dot in enumerate(self._dots):
            if i == self._step:
                dot.setStyleSheet(f"color: {step['icon_color']}; font-size: 12px;")
            elif i < self._step:
                dot.setStyleSheet("color: #475569; font-size: 10px;")
            else:
                dot.setStyleSheet("color: #334155; font-size: 10px;")

        self._btn_prev.setVisible(self._step > 0)

        is_last = self._step == total - 1
        self._btn_next.setText("Concluir" if is_last else "Próximo")
        self._btn_skip.setVisible(not is_last)

    def _next(self):
        if self._step < len(STEPS) - 1:
            self._step += 1
            self._update_step()
        else:
            self._finish()

    def _prev(self):
        if self._step > 0:
            self._step -= 1
            self._update_step()

    def _finish(self):
        self.finished.emit()
        self.hide()
