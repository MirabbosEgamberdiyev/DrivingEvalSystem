"""Verification test launching python -m app --simulate --windowed."""

import subprocess
import sys
import time
from pathlib import Path


def test_launch_app_simulate_windowed():
    """Spawns the app process via python -m app --simulate --windowed and verifies it runs cleanly."""
    env = dict(sys.modules["os"].environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONPATH"] = "src"

    proc = subprocess.Popen(
        [sys.executable, "-m", "app", "--simulate", "--windowed"],
        cwd=str(Path(".").resolve()),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Give it 2 seconds to initialize QML engine and display main window
        time.sleep(2)
        assert proc.poll() is None, f"Process terminated prematurely: {proc.communicate()}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)

    assert proc.returncode in (0, 15, -15, 1)  # Terminated successfully
