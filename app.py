"""Root launcher for Driving Training & Evaluation System.

Allows running:
    python -m app --simulate --windowed
    python app.py --simulate --windowed
"""

import sys
from pathlib import Path

# Add src to sys.path
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from driving_eval.ui_qml.app import run_qml_app  # noqa: E402

if __name__ == "__main__":
    sys.exit(run_qml_app())
