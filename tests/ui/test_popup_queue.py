"""Test sequential violation popup queue handling in QML."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine


def test_violation_popup_queue_serialization(qapp, qtbot):
    """Verifies that multiple violations queue sequentially without overlapping."""
    engine = QQmlApplicationEngine()
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    engine.addImportPath(str(qml_dir))

    popup_file = qml_dir / "components" / "ViolationPopup.qml"
    engine.load(QUrl.fromLocalFile(str(popup_file)))
    assert len(engine.rootObjects()) > 0
    popup = engine.rootObjects()[0]

    def get_queue(p):
        val = p.property("queue")
        return val.toVariant() if hasattr(val, "toVariant") else val

    def get_current(p):
        val = p.property("currentItem")
        return val.toVariant() if hasattr(val, "toVariant") else val

    assert popup.property("isShowing") is False
    assert len(get_queue(popup)) == 0

    # 1. Enqueue first violation
    popup.enqueue("CONE_TOUCH", "Konusga tegish", "Konusga tegish holati", 10, False)
    assert popup.property("isShowing") is True
    cur1 = get_current(popup)
    assert cur1["code"] == "CONE_TOUCH"
    assert cur1["penalty"] == 10
    assert len(get_queue(popup)) == 0

    # 2. Enqueue two more violations rapidly while first is showing
    popup.enqueue("LINE_TOUCH", "Chiziq bosish", "Yon chiziq ustiga chiqildi", 5, False)
    popup.enqueue("STOP_LINE_FAIL", "Stop chiziq", "Stop chiziqda to'xtamadi", 100, True)

    # First violation is still showing, queue has 2 items
    assert popup.property("isShowing") is True
    assert get_current(popup)["code"] == "CONE_TOUCH"
    assert len(get_queue(popup)) == 2

    # 3. Dismiss current (first) violation -> second violation shows immediately
    popup.dismissCurrent()
    assert popup.property("isShowing") is True
    cur2 = get_current(popup)
    assert cur2["code"] == "LINE_TOUCH"
    assert cur2["penalty"] == 5
    assert len(get_queue(popup)) == 1

    # 4. Dismiss second violation -> third (critical) violation shows
    popup.dismissCurrent()
    assert popup.property("isShowing") is True
    cur3 = get_current(popup)
    assert cur3["code"] == "STOP_LINE_FAIL"
    assert cur3["critical"] is True
    assert len(get_queue(popup)) == 0

    # 5. Dismiss third violation -> queue empty, isShowing becomes False
    popup.dismissCurrent()
    assert popup.property("isShowing") is False
    assert get_current(popup) is None
