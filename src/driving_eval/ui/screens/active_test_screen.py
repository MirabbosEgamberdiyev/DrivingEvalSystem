"""Active test examination screen displaying minimalist high-contrast HUD."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from driving_eval.ui.components.violation_popup import PopupQueueManager, ViolationPopupWidget
from driving_eval.ui.i18n import tr


class ActiveTestScreen(QWidget):
    """High-contrast dashboard during active exam (only time, speed, exercise, penalty, error count)."""

    finish_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        # Top Overlay Popup
        self.popup_widget = ViolationPopupWidget(self)
        self.popup_manager = PopupQueueManager(self.popup_widget, duration_seconds=3.5)

        # Header Exercise Bar
        ex_frame = QFrame()
        ex_frame.setStyleSheet("background-color: #1A365D; border-radius: 12px; padding: 15px;")
        ex_layout = QHBoxLayout(ex_frame)
        ex_title = QLabel("JORIY MASHQ:")
        ex_title.setFont(QFont("Arial", 16, QFont.Bold))
        ex_title.setStyleSheet("color: #90CDF4;")
        self.exercise_label = QLabel("START")
        self.exercise_label.setFont(QFont("Arial", 22, QFont.Bold))
        self.exercise_label.setStyleSheet("color: white;")
        ex_layout.addWidget(ex_title)
        ex_layout.addWidget(self.exercise_label)
        ex_layout.addStretch()
        layout.addWidget(ex_frame)
        layout.addSpacing(25)

        # 4 HUD Stat Cards
        hud_layout = QHBoxLayout()
        hud_layout.setSpacing(20)

        self.card_time = self._create_hud_card(tr("hud_time"), "00:00", "#4A5568")
        self.card_speed = self._create_hud_card(tr("hud_speed"), "0.0 km/h", "#2B6CB0")
        self.card_penalty = self._create_hud_card(tr("hud_penalty"), "0 BALL", "#C53030")
        self.card_errors = self._create_hud_card(tr("hud_violations_count"), "0", "#DD6B20")

        hud_layout.addWidget(self.card_time)
        hud_layout.addWidget(self.card_speed)
        hud_layout.addWidget(self.card_penalty)
        hud_layout.addWidget(self.card_errors)
        layout.addLayout(hud_layout)
        layout.addStretch()

        # Bottom Finish Button: Strictly enabled only when vehicle is stopped in finish zone!
        btn_frame = QHBoxLayout()
        btn_frame.addStretch()
        self.btn_finish = QPushButton(tr("btn_finish_test"))
        self.btn_finish.setEnabled(False)
        self.btn_finish.setFixedWidth(350)
        self.btn_finish.setStyleSheet("""
            QPushButton {
                background-color: #E53E3E;
                border-radius: 10px;
                color: white;
                font-size: 18px;
                font-weight: bold;
                padding: 18px;
            }
            QPushButton:disabled {
                background-color: #2D3748;
                color: #718096;
            }
            QPushButton:hover:!disabled {
                background-color: #C53030;
            }
        """)
        self.btn_finish.clicked.connect(self.finish_requested.emit)
        btn_frame.addWidget(self.btn_finish)
        btn_frame.addStretch()
        layout.addLayout(btn_frame)

    def _create_hud_card(self, title: str, initial_value: str, border_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1A202C;
                border: 2px solid {border_color};
                border-radius: 12px;
                padding: 20px;
            }}
            QLabel {{ color: white; }}
        """)
        c_layout = QVBoxLayout(card)
        c_title = QLabel(title)
        c_title.setFont(QFont("Arial", 13))
        c_title.setStyleSheet("color: #A0AEC0;")

        val_label = QLabel(initial_value)
        val_label.setFont(QFont("Arial", 28, QFont.Bold))
        val_label.setAlignment(Qt.AlignCenter)

        c_layout.addWidget(c_title)
        c_layout.addWidget(val_label)
        card.value_label = val_label  # type: ignore[attr-defined]
        return card

    def update_hud(
        self,
        elapsed_seconds: int,
        speed_kmh: float,
        exercise: str,
        total_penalty: int,
        violation_count: int,
        can_finish: bool,
    ) -> None:
        mins = elapsed_seconds // 60
        secs = elapsed_seconds % 60
        self.card_time.value_label.setText(f"{mins:02d}:{secs:02d}")  # type: ignore[attr-defined]
        self.card_speed.value_label.setText(f"{speed_kmh:.1f} km/h")  # type: ignore[attr-defined]
        self.card_penalty.value_label.setText(f"-{total_penalty}")  # type: ignore[attr-defined]
        self.card_errors.value_label.setText(str(violation_count))  # type: ignore[attr-defined]
        self.exercise_label.setText(exercise)
        self.btn_finish.setEnabled(can_finish)
