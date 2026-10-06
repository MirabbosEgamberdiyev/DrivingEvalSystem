"""Violation popup notification overlay with queue management and non-blocking display."""

from collections import deque

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from driving_eval.rules.event_manager import ProcessedViolationEvent


class ViolationPopupWidget(QFrame):
    """Floating transparent overlay displaying single violation details for 3.5 seconds."""

    dismissed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.SubWindow | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(550)
        self.setFixedHeight(120)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)

        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 14, QFont.Bold))

        self.desc_label = QLabel()
        self.desc_label.setFont(QFont("Arial", 11))
        self.desc_label.setWordWrap(True)

        self.penalty_label = QLabel()
        self.penalty_label.setFont(QFont("Arial", 12, QFont.Bold))

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.penalty_label)

        layout.addLayout(top_layout)
        layout.addWidget(self.desc_label)

        self.hide()

    def show_event(self, event: ProcessedViolationEvent, duration_ms: int = 3500) -> None:
        if event.critical:
            bg_color = "#E53E3E"  # Critical Red
            title_text = "KRITIK QOIDABUZARLIK!"
            pen_text = f"-{event.penalty} BALL"
        else:
            bg_color = "#DD6B20"  # Violation Orange
            title_text = "QOIDABUZARLIK ANIQLANDI"
            pen_text = f"-{event.penalty} BALL" if event.status == "CONFIRMED" else "SUSPECT (0 ball)"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid white;
                border-radius: 12px;
                color: white;
            }}
            QLabel {{
                color: white;
            }}
        """)
        self.title_label.setText(title_text)
        self.desc_label.setText(f"{event.screen_text} ({event.details})")
        self.penalty_label.setText(pen_text)

        # Center horizontally at top
        if self.parentWidget():
            pw = self.parentWidget().width()
            self.move((pw - self.width()) // 2, 40)

        self.show()
        self.raise_()
        self._timer.start(duration_ms)

    def _on_timeout(self) -> None:
        self.hide()
        self.dismissed.emit()


class PopupQueueManager:
    """Manages queue of popups so consecutive violations display sequentially without overlap."""

    def __init__(self, popup_widget: ViolationPopupWidget, duration_seconds: float = 3.5):
        self.popup = popup_widget
        self.duration_ms = int(duration_seconds * 1000)
        self._queue: deque[ProcessedViolationEvent] = deque()
        self._is_showing = False

        self.popup.dismissed.connect(self._show_next)

    def enqueue(self, event: ProcessedViolationEvent) -> None:
        self._queue.append(event)
        if not self._is_showing:
            self._show_next()

    def _show_next(self) -> None:
        if not self._queue:
            self._is_showing = False
            return

        self._is_showing = True
        next_event = self._queue.popleft()
        self.popup.show_event(next_event, self.duration_ms)
