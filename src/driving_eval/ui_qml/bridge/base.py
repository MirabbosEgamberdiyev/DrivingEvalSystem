"""Abstract Base Bridge connecting the QML UI to the evaluation backend.

Ensures strict separation of concerns: UI only renders state and dispatches commands.
"""

from abc import abstractmethod

from PySide6.QtCore import Property, QObject, Signal, Slot


class BackendBridge(QObject):
    """Abstract interface for all UI-to-Backend communications."""

    # --- Signals for state & telemetry updates ---
    stateChanged = Signal(str)
    precheckUpdated = Signal(list)  # list of dicts: [{name, status, detail, required}]
    liveStatusUpdated = Signal(int, float, str, int, int)  # time, speed, exercise, penalty, count
    violationRaised = Signal(str, str, str, int, bool)  # code, title, screenText, penalty, critical
    finishReadyChanged = Signal(bool)
    resultReady = Signal(dict)
    violationsListReady = Signal(list)
    evidenceReady = Signal(dict)
    connectionStatusChanged = Signal(bool)
    settingsUnlockedChanged = Signal(bool)
    lockoutRemainingChanged = Signal(int)
    usbExportFinished = Signal(bool, str)
    sessionsListReady = Signal(list)
    systemDiagnosticsUpdated = Signal(dict)
    reportExportFinished = Signal(bool, str)
    hashVerificationFinished = Signal(str, bool, str)
    roleChanged = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._current_state: str = "HOME"
        self._current_role: str = "STUDENT"  # 'STUDENT', 'INSPECTOR', 'ADMIN'
        self._finish_ready: bool = False
        self._is_connected: bool = True
        self._car_id: str = "CAR-01"
        self._rules_version: str = "v1.0-official"
        self._precheck_passed: bool = False
        self._precheck_blocked_reason: str = ""
        self._settings_unlocked: bool = False
        self._lockout_remaining: int = 0

    # --- Properties accessible from QML ---

    def get_current_state(self) -> str:
        return self._current_state

    def set_current_state(self, state: str) -> None:
        if self._current_state != state:
            self._current_state = state
            self.stateChanged.emit(state)

    currentState = Property(str, get_current_state, set_current_state, notify=stateChanged)

    def get_finish_ready(self) -> bool:
        return self._finish_ready

    def set_finish_ready(self, ready: bool) -> None:
        if self._finish_ready != ready:
            self._finish_ready = ready
            self.finishReadyChanged.emit(ready)

    finishReady = Property(bool, get_finish_ready, set_finish_ready, notify=finishReadyChanged)

    def get_is_connected(self) -> bool:
        return self._is_connected

    def set_is_connected(self, connected: bool) -> None:
        if self._is_connected != connected:
            self._is_connected = connected
            self.connectionStatusChanged.emit(connected)

    isConnected = Property(bool, get_is_connected, set_is_connected, notify=connectionStatusChanged)

    def get_car_id(self) -> str:
        return self._car_id

    carId = Property(str, get_car_id, constant=True)

    def get_rules_version(self) -> str:
        return self._rules_version

    rulesVersion = Property(str, get_rules_version, constant=True)

    def get_precheck_passed(self) -> bool:
        return self._precheck_passed

    precheckPassed = Property(bool, get_precheck_passed, notify=precheckUpdated)

    def get_precheck_blocked_reason(self) -> str:
        return self._precheck_blocked_reason

    precheckBlockedReason = Property(str, get_precheck_blocked_reason, notify=precheckUpdated)

    def get_settings_unlocked(self) -> bool:
        return self._settings_unlocked

    settingsUnlocked = Property(bool, get_settings_unlocked, notify=settingsUnlockedChanged)

    def get_lockout_remaining(self) -> int:
        return self._lockout_remaining

    lockoutRemaining = Property(int, get_lockout_remaining, notify=lockoutRemainingChanged)

    def get_current_role(self) -> str:
        return self._current_role

    def set_current_role(self, role: str) -> None:
        if self._current_role != role:
            self._current_role = role
            self.roleChanged.emit(role)

    currentRole = Property(str, get_current_role, set_current_role, notify=roleChanged)

    # --- Abstract Commands (Slots invoked from QML) ---

    @Slot()
    @abstractmethod
    def startPrecheck(self) -> None:
        """Triggers precheck diagnostics."""
        pass

    @Slot()
    @abstractmethod
    def retryPrecheck(self) -> None:
        """Retries failed precheck diagnostics."""
        pass

    @Slot()
    @abstractmethod
    def startTest(self) -> None:
        """Transitions to active test."""
        pass

    @Slot()
    @abstractmethod
    def finishTest(self) -> None:
        """Finalizes the active exam."""
        pass

    @Slot()
    @abstractmethod
    def requestViolations(self) -> None:
        """Requests the list of recorded violations for the current or last session."""
        pass

    @Slot(str)
    @abstractmethod
    def openEvidence(self, event_id: str) -> None:
        """Requests media evidence for the given violation event ID."""
        pass

    @Slot(str)
    @abstractmethod
    def adminLogin(self, pin: str) -> None:
        """Verifies admin PIN code with lockout protection."""
        pass

    @Slot()
    @abstractmethod
    def adminLogout(self) -> None:
        """Locks settings screen."""
        pass

    @Slot()
    @abstractmethod
    def exportUsb(self) -> None:
        """Exports exam report, evidence, and database logs to connected USB."""
        pass

    @Slot()
    @abstractmethod
    def resetToHome(self) -> None:
        """Resets application to HOME state for the next candidate."""
        pass

    @Slot()
    @abstractmethod
    def requestSessions(self) -> None:
        """Requests list of historical exam sessions for Inspector Mode."""
        pass

    @Slot()
    @abstractmethod
    def requestDiagnostics(self) -> None:
        """Requests real-time hardware and sensor telemetry diagnostics."""
        pass

    @Slot(str)
    @abstractmethod
    def verifySessionHash(self, session_id: str) -> None:
        """Verifies SHA-256 hash chain and digital signature for session."""
        pass

    @Slot(str)
    @abstractmethod
    def exportSessionPdf(self, session_id: str) -> None:
        """Generates and exports official PDF report for session."""
        pass
