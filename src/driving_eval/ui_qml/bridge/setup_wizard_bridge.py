"""QML UI Bridge for the Setup Wizard screen.

Provides Qt signals, slots, and properties connecting SetupWizardScreen.qml
with the underlying SetupWizardService.
"""

import logging

from PySide6.QtCore import QObject, Signal, Slot

from driving_eval.wizard.setup_service import SetupWizardService

logger = logging.getLogger("driving_eval.ui.setup_wizard_bridge")


class SetupWizardBridge(QObject):
    """Bridge exposing Setup Wizard actions and states to QML UI."""

    stepChanged = Signal(str, int)  # step_name, step_index
    hardwareReportReady = Signal(str, str, str, str, bool)  # cpu, ram, disk, gpu, is_safe
    calibrationReportReady = Signal(float, bool, str)  # max_drift_cm, is_valid, warning
    audioTestPlayed = Signal(bool)
    wizardSaved = Signal(bool)
    canProceedChanged = Signal(bool)

    def __init__(self, wizard_service: SetupWizardService, parent: QObject | None = None):
        super().__init__(parent)
        self.wizard = wizard_service

    @Slot(result=int)
    def getCurrentStepIndex(self) -> int:
        return self.wizard.current_step_index

    @Slot(result=int)
    def getTotalSteps(self) -> int:
        return self.wizard.total_steps

    @Slot(result=str)
    def getSelectedLanguage(self) -> str:
        return self.wizard.selected_language

    @Slot(result=bool)
    def canProceed(self) -> bool:
        return self.wizard.can_proceed()

    @Slot(str)
    def selectLanguage(self, lang: str) -> None:
        self.wizard.confirm_language_and_eula(lang, self.wizard.eula_agreed)
        self.canProceedChanged.emit(self.wizard.can_proceed())

    @Slot(bool)
    def setEulaAgreed(self, agreed: bool) -> None:
        self.wizard.confirm_language_and_eula(self.wizard.selected_language, agreed)
        self.canProceedChanged.emit(self.wizard.can_proceed())

    @Slot()
    def runHardwareScan(self) -> None:
        hw = self.wizard.analyze_hardware_and_usb()
        cpu_str = f"{hw.cpu_cores} Cores"
        ram_str = f"{hw.ram_gb:.1f} GB RAM"
        disk_str = f"{hw.free_disk_gb:.1f} GB Free"
        gpu_str = hw.gpu_backend
        self.hardwareReportReady.emit(cpu_str, ram_str, disk_str, gpu_str, hw.is_usb_bandwidth_safe)
        self.canProceedChanged.emit(self.wizard.can_proceed())

    @Slot(str, str)
    def setCameraSource(self, camera_name: str, source: str) -> None:
        self.wizard.configure_camera_mapping(camera_name, source, [1920, 1080], 30)
        self.canProceedChanged.emit(self.wizard.can_proceed())

    @Slot()
    def runCalibrationCheck(self) -> None:
        calib = self.wizard.verify_calibration()
        warn_msg = calib.warning or ""
        self.calibrationReportReady.emit(calib.max_drift_cm, calib.is_valid, warn_msg)
        self.canProceedChanged.emit(self.wizard.can_proceed())

    @Slot()
    def playAudioTest(self) -> None:
        ok = self.wizard.test_audio_output()
        self.audioTestPlayed.emit(ok)
        self.canProceedChanged.emit(self.wizard.can_proceed())

    @Slot()
    def nextStep(self) -> None:
        success, step_name = self.wizard.next_step()
        if success:
            self.stepChanged.emit(step_name, self.wizard.current_step_index)
            self.canProceedChanged.emit(self.wizard.can_proceed())

    @Slot()
    def prevStep(self) -> None:
        success, step_name = self.wizard.prev_step()
        if success:
            self.stepChanged.emit(step_name, self.wizard.current_step_index)
            self.canProceedChanged.emit(self.wizard.can_proceed())

    @Slot()
    def saveAndComplete(self) -> None:
        ok = self.wizard.finalize_and_save_configuration()
        self.wizardSaved.emit(ok)
