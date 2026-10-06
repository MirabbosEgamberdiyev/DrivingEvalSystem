"""Package-level app runner when src is in PYTHONPATH."""

import sys

from driving_eval.ui_qml.app import run_qml_app

if __name__ == "__main__":
    sys.exit(run_qml_app())
