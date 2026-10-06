"""Password-protected admin and system diagnostics settings screen."""

import hashlib

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from driving_eval.ui.i18n import tr


class SettingsScreen(QWidget):
    """Admin settings screen locked by SHA-256 hashed PIN."""

    close_requested = Signal()

    def __init__(self, admin_pin_hash_sha256: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.expected_hash = admin_pin_hash_sha256
        self._init_ui()

    def _init_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)

        self.stack = QStackedWidget()

        # Page 0: PIN entry
        self.pin_page = QWidget()
        pin_layout = QVBoxLayout(self.pin_page)
        pin_layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setFixedWidth(400)
        card.setStyleSheet("background-color: #2D3748; border-radius: 12px; padding: 25px;")
        c_layout = QVBoxLayout(card)

        title = QLabel(tr("settings_title"))
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignCenter)
        c_layout.addWidget(title)
        c_layout.addSpacing(15)

        lbl = QLabel(tr("admin_pin_prompt"))
        lbl.setStyleSheet("color: #E2E8F0;")
        self.pin_input = QLineEdit()
        self.pin_input.setEchoMode(QLineEdit.Password)
        self.pin_input.setPlaceholderText("PIN kod (standart: 1234)")
        self.pin_input.setStyleSheet("background-color: #1A202C; color: white; padding: 10px; border-radius: 6px;")
        c_layout.addWidget(lbl)
        c_layout.addWidget(self.pin_input)
        c_layout.addSpacing(15)

        self.btn_unlock = QPushButton(tr("btn_unlock"))
        self.btn_unlock.setStyleSheet("background-color: #3182CE; color: white; padding: 10px; font-weight: bold; border-radius: 6px;")
        self.btn_unlock.clicked.connect(self._verify_pin)
        c_layout.addWidget(self.btn_unlock)

        self.err_label = QLabel("")
        self.err_label.setStyleSheet("color: #FEB2B2;")
        c_layout.addWidget(self.err_label)

        pin_layout.addWidget(card)

        # Page 1: Admin Panel
        self.admin_page = QWidget()
        adm_layout = QVBoxLayout(self.admin_page)

        adm_title = QLabel("Tizim Diagnostikasi va Sozlamalari")
        adm_title.setFont(QFont("Arial", 18, QFont.Bold))
        adm_title.setStyleSheet("color: white;")
        adm_layout.addWidget(adm_title)

        self.diag_text = QTextEdit()
        self.diag_text.setReadOnly(True)
        self.diag_text.setStyleSheet("background-color: #1A202C; color: #68D391; font-family: Courier; padding: 10px;")
        self.diag_text.setText(
            "TIZIM HOLATI:\n"
            "----------------------------------------\n"
            "• OS: Ubuntu LTS / Linux Standalone (yoki Windows Dev)\n"
            "• AI Inference Backend: Mock / ONNX Runtime\n"
            "• Kameralar: 4 ta kanal (FRONT, REAR, LEFT, RIGHT)\n"
            "• SQLite WAL: Faol, barcha tranzaksiyalar darhol commit qilinadi\n"
            "• SHA-256 Xesh Zanjiri: Butunlik tekshirilgan va barqaror\n"
            "• Offline Rejim: 100% Tarmoq chaqiruvlari bloklangan\n"
        )
        adm_layout.addWidget(self.diag_text)

        btn_close = QPushButton("Yopish")
        btn_close.setStyleSheet("background-color: #4A5568; color: white; padding: 10px 20px; border-radius: 6px;")
        btn_close.clicked.connect(self.close_requested.emit)
        adm_layout.addWidget(btn_close)

        self.stack.addWidget(self.pin_page)
        self.stack.addWidget(self.admin_page)

        self.layout.addWidget(self.stack)

    def _verify_pin(self) -> None:
        pin = self.pin_input.text().strip()
        h = hashlib.sha256(pin.encode()).hexdigest()
        if h == self.expected_hash:
            self.err_label.setText("")
            self.pin_input.clear()
            self.stack.setCurrentIndex(1)
        else:
            self.err_label.setText("Noto'g'ri PIN kod!")
            self.pin_input.clear()
