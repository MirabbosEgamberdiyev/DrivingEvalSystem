"""Process watchdog for multi-process heartbeat monitoring and automated recovery."""

import logging
import threading
import time
from collections.abc import Callable

logger = logging.getLogger("driving_eval.maintenance.watchdog")


class ProcessWatchdog:
    """Monitors worker heartbeat timestamps and triggers recovery if a process freezes."""

    def __init__(
        self,
        heartbeat_timeout_seconds: float = 6.0,
        check_interval_seconds: float = 2.0,
        restart_callback: Callable[[str], None] | None = None,
    ):
        self.timeout = heartbeat_timeout_seconds
        self.check_interval = check_interval_seconds
        self.restart_callback = restart_callback

        self._heartbeats: dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def register_process(self, name: str) -> None:
        with self._lock:
            self._heartbeats[name] = time.monotonic()

    def record_heartbeat(self, name: str) -> None:
        with self._lock:
            self._heartbeats[name] = time.monotonic()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, name="WatchdogWorker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _monitor_loop(self) -> None:
        while self._running:
            now = time.monotonic()
            dead_workers = []

            with self._lock:
                for name, last_time in self._heartbeats.items():
                    elapsed = now - last_time
                    if elapsed > self.timeout:
                        dead_workers.append((name, elapsed))

            for name, elapsed in dead_workers:
                logger.error(
                    "WATCHDOG OGOHLANTIRISH: Jarayon '%s' javob bermayapti! (So'nggi signal: %.1fs oldin)",
                    name, elapsed
                )
                if self.restart_callback:
                    try:
                        self.restart_callback(name)
                        # Reset heartbeat to give process time to re-initialize
                        with self._lock:
                            self._heartbeats[name] = time.monotonic()
                    except Exception as e:
                        logger.error("Jarayonni qayta ishga tushirishda xato: %s", e)

            time.sleep(self.check_interval)
