"""Pre-check status screen displaying live diagnostic cards."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from driving_eval.hardware.precheck import PrecheckReport
from driving_eval.ui.i18n import tr


class PrecheckScreen(QWidget):
    """Pre-check verification screen with explicit blocks if any mandatory item fails."""

    recheck_requested = Signal()
    proceed_to_test_ready = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel(tr("precheck_title"))
        header.setFont(QFont("Arial", 18, QFont.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)

        # Warning / Status banner
        self.status_banner = QLabel("Tizim tekshirilmoqda...")
        self.status_banner.setFont(QFont("Arial", 12, QFont.Bold))
        self.status_banner.setWordWrap(True)
        self.status_banner.setStyleSheet("padding: 10px; border-radius: 8px; background-color: #2D3748; color: white;")
        layout.addWidget(self.status_banner)
        layout.addSpacing(10)

        # Grid of cards in a scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: transparent; border: none;")

        self.cards_container = QWidget()
        self.cards_layout = QGridLayout(self.cards_container)
        self.cards_layout.setSpacing(15)
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll)

        # Bottom Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_recheck = QPushButton(tr("btn_recheck"))
        self.btn_recheck.setStyleSheet("""
            QPushButton {
                background-color: #4A5568;
                border-radius: 8px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 12px 25px;
            }
            QPushButton:hover { background-color: #718096; }
        """)
        self.btn_recheck.clicked.connect(self.recheck_requested.emit)
        btn_layout.addWidget(self.btn_recheck)

        btn_layout.addStretch()

        self.btn_proceed = QPushButton(tr("btn_to_test_ready"))
        self.btn_proceed.setEnabled(False)
        self.btn_proceed.setStyleSheet("""
            QPushButton {
                background-color: #38A169;
                border-radius: 8px;
                color: white;
                font-size: 15px;
                font-weight: bold;
                padding: 12px 25px;
            }
            QPushButton:disabled { background-color: #2D3748; color: #718096; }
            QPushButton:hover:!disabled { background-color: #2F855A; }
        """)
        self.btn_proceed.clicked.connect(self.proceed_to_test_ready.emit)
        btn_layout.addWidget(self.btn_proceed)

        layout.addLayout(btn_layout)

    def display_report(self, report: PrecheckReport) -> None:
        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Update Banner
        if report.passed:
            self.status_banner.setText("Barcha tizimlar soz holatda. Imtihonni boshlash mumkin.")
            self.status_banner.setStyleSheet("padding: 10px; border-radius: 8px; background-color: #22543D; color: #9AE6B4;")
            self.btn_proceed.setEnabled(True)
        else:
            reasons_str = "\n• " + "\n• ".join(report.block_reasons)
            self.status_banner.setText(f"{tr('precheck_blocked')}{reasons_str}")
            self.status_banner.setStyleSheet("padding: 10px; border-radius: 8px; background-color: #742A2A; color: #FEB2B2;")
            self.btn_proceed.setEnabled(False)

        # Render Item Cards
        row, col = 0, 0
        for item in report.items:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {'#1C3A27' if item.passed else '#431B1B'};
                    border: 1px solid {'#38A169' if item.passed else '#E53E3E'};
                    border-radius: 8px;
                    padding: 10px;
                }}
                QLabel {{ color: white; }}
            """)
            c_layout = QVBoxLayout(card)

            status_icon = "✔ TAYYOR" if item.passed else "✖ NOSOZ"
            top_row = QHBoxLayout()
            c_title = QLabel(item.name)
            c_title.setFont(QFont("Arial", 11, QFont.Bold))
            c_status = QLabel(status_icon)
            c_status.setFont(QFont("Arial", 10, QFont.Bold))
            c_status.setStyleSheet(f"color: {'#68D391' if item.passed else '#FC8181'};")
            top_row.addWidget(c_title)
            top_row.addStretch()
            top_row.addWidget(c_status)

            c_details = QLabel(item.details)
            c_details.setFont(QFont("Arial", 9))
            c_details.setWordWrap(True)

            c_layout.addLayout(top_row)
            c_layout.addWidget(c_details)

            self.cards_layout.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
