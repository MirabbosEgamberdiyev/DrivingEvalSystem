"""HOME screen for candidate registration and initiating pre-check."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from driving_eval.ui.i18n import tr


class HomeScreen(QWidget):
    """Home screen where candidate details are verified before test initiation."""

    precheck_requested = Signal(dict)
    open_settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFixedWidth(650)
        card.setStyleSheet("""
            QFrame {
                background-color: #2D3748;
                border-radius: 12px;
                padding: 25px;
            }
            QLabel {
                color: #EDF2F7;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #1A202C;
                border: 1px solid #4A5568;
                border-radius: 6px;
                color: #FFFFFF;
                padding: 10px;
                font-size: 15px;
            }
            QPushButton {
                background-color: #3182CE;
                border-radius: 8px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #2B6CB0;
            }
        """)

        card_layout = QVBoxLayout(card)

        title = QLabel(tr("app_title"))
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title)
        card_layout.addSpacing(15)

        form_layout = QFormLayout()
        self.passport_input = QLineEdit()
        self.passport_input.setPlaceholderText("AA1234567")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Aziz")

        self.surname_input = QLineEdit()
        self.surname_input.setPlaceholderText("Rahimov")

        form_layout.addRow(tr("student_passport"), self.passport_input)
        form_layout.addRow(tr("student_name"), self.name_input)
        form_layout.addRow(tr("student_surname"), self.surname_input)

        card_layout.addLayout(form_layout)
        card_layout.addSpacing(25)

        self.btn_precheck = QPushButton(tr("btn_start_precheck"))
        self.btn_precheck.clicked.connect(self._on_precheck_clicked)
        card_layout.addWidget(self.btn_precheck)

        main_layout.addWidget(card)

        # Bottom settings button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.btn_settings = QPushButton("⚙ Sozlamalar")
        self.btn_settings.setStyleSheet("background-color: transparent; color: #A0AEC0; font-size: 12px;")
        self.btn_settings.clicked.connect(self.open_settings_requested.emit)
        bottom_layout.addWidget(self.btn_settings)
        main_layout.addLayout(bottom_layout)

    def _on_precheck_clicked(self) -> None:
        data = {
            "passport_id": self.passport_input.text().strip() or "AA1234567",
            "first_name": self.name_input.text().strip() or "Aziz",
            "last_name": self.surname_input.text().strip() or "Rahimov",
        }
        self.precheck_requested.emit(data)
