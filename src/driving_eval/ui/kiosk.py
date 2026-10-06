"""Kiosk mode configuration and security key blocking."""

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QWidget


class KioskEventFilter(QObject):
    """Filters out hotkeys that could exit kiosk mode (Alt+Tab, Esc, Alt+F4)."""

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.KeyPress:
            # Block Escape or system navigation keys
            if event.key() in (Qt.Key_Escape, Qt.Key_Alt, Qt.Key_Super_L, Qt.Key_Super_R):
                return True
        return super().eventFilter(watched, event)


def apply_kiosk_mode(window: QWidget, enabled: bool = True) -> None:
    """Configures fullscreen, frameless kiosk mode on a QWidget/QMainWindow."""
    if not enabled:
        return

    window.setWindowFlags(
        Qt.Window
        | Qt.FramelessWindowHint
        | Qt.WindowStaysOnTopHint
    )
    window.showFullScreen()
    filter_obj = KioskEventFilter(window)
    window.installEventFilter(filter_obj)
