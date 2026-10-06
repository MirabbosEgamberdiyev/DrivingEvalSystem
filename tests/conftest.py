"""Global pytest fixtures for Qt applications (QtWidgets and QtQuick/QML)."""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Provides a single session-scoped QApplication supporting QtWidgets and QtQuick."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
