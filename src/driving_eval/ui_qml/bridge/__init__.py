"""Bridge layer connecting QML UI to backend services."""

from driving_eval.ui_qml.bridge.base import BackendBridge
from driving_eval.ui_qml.bridge.mock_bridge import MockBridge
from driving_eval.ui_qml.bridge.real_bridge import RealBridge
from driving_eval.ui_qml.bridge.setup_wizard_bridge import SetupWizardBridge

__all__ = ["BackendBridge", "MockBridge", "RealBridge", "SetupWizardBridge"]
