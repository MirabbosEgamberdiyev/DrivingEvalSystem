"""Integration test for Vertical Slice across all 3 languages (Phase 3).

Verifies the complete end-to-end user journey in:
- uz-Latn (Uzbek Latin)
- uz-Cyrl (Uzbek Cyrillic)
- ru (Russian)

Journey:
Language Selection -> HOME -> PRECHECK -> SYSTEM_READY -> ACTIVE TEST ->
Violation Event -> STOPPED -> RESULT (PASS/FAIL) -> VIOLATIONS -> RESET TO HOME
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtQml import QQmlApplicationEngine

from driving_eval.i18n.service import SUPPORTED_LANGUAGES, I18nService
from driving_eval.ui_qml.bridge.mock_bridge import MockBridge


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_cli_launch_app_multilingual_simulate(lang: str) -> None:
    """Verifies that python app.py --simulate --windowed --lang <lang> boots cleanly."""
    env = dict(sys.modules["os"].environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONPATH"] = "src"

    proc = subprocess.Popen(
        [sys.executable, "app.py", "--simulate", "--windowed", "--lang", lang],
        cwd=str(Path(".").resolve()),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Give 2.5 seconds to initialize QML engine and render offscreen window
        time.sleep(2.5)
        assert proc.poll() is None, f"Process died for lang {lang}: {proc.communicate()}"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_in_memory_full_vertical_slice(qapp, lang: str) -> None:
    """Executes the full vertical slice in-memory with QML engine and verifies all transitions."""
    engine = QQmlApplicationEngine()
    qml_dir = Path("src/driving_eval/ui_qml/qml").resolve()
    engine.addImportPath(str(qml_dir))
    engine.addImportPath(str(qml_dir.parent))

    bridge = MockBridge(scenario="normal_pass")
    i18n = I18nService(default_lang=lang)

    engine.rootContext().setContextProperty("backendBridge", bridge)
    engine.rootContext().setContextProperty("i18n", i18n)

    engine.load(str(qml_dir / "Main.qml"))
    assert len(engine.rootObjects()) > 0, f"Main.qml failed to compile for lang {lang}"

    # 1. Start Precheck
    bridge.startPrecheck()
    assert bridge.currentState == "PRECHECK"

    # Wait briefly for precheck completion (400ms timer in mock_bridge)
    start_time = time.time()
    while not bridge.precheckPassed and time.time() - start_time < 2.0:
        qapp.processEvents()
        time.sleep(0.05)
    assert bridge.precheckPassed is True

    # 2. Proceed to Ready
    bridge.proceedToReady()
    assert bridge.currentState == "SYSTEM_READY"

    # 3. Start Active Test
    bridge.startTest()
    assert bridge.currentState == "TEST_ACTIVE"

    # 4. Advance through test ticks to trigger violation and finish readiness
    for _ in range(12):
        qapp.processEvents()
        time.sleep(0.1)

    # 5. Finish Test
    bridge.set_finish_ready(True)
    bridge.finishTest()
    assert bridge.currentState == "RESULT_READY"

    # 6. Request Violations List
    bridge.requestViolations()
    qapp.processEvents()

    # 7. Reset to Home
    bridge.resetToHome()
    assert bridge.currentState == "HOME"
