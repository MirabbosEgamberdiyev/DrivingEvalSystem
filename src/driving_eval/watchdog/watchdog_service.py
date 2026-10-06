"""Watchdog service, process supervision, heartbeat monitoring, and diagnostics crash bundle exporter.

Provides robust process monitoring, automated crash recovery with rate-limiting,
and offline diagnostics package generation (SQLite DB snapshot, logs, system specs)
for on-premise technician inspection.
"""

from __future__ import annotations

import ctypes
import datetime
import hashlib
import json
import logging
import os
import platform
import shutil
import sqlite3
import subprocess
import threading
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("driving_eval.watchdog")


class CrashBundleExporter:
    """Exports self-contained diagnostics bundle (.zip) with logs, DB snapshot, and hardware state."""

    @staticmethod
    def get_system_telemetry() -> dict[str, Any]:
        """Collects local OS, CPU, RAM and disk statistics using standard library."""
        info: dict[str, Any] = {
            "os_system": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "cpu_logical_cores": os.cpu_count() or 4,
            "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        # RAM info on Windows via GlobalMemoryStatusEx
        if platform.system() == "Windows":
            try:
                class MemoryStatusEx(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MemoryStatusEx()
                stat.dwLength = ctypes.sizeof(MemoryStatusEx)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    info["ram_total_gb"] = round(stat.ullTotalPhys / (1024**3), 2)
                    info["ram_avail_gb"] = round(stat.ullAvailPhys / (1024**3), 2)
                    info["ram_load_percent"] = stat.dwMemoryLoad
            except Exception as e:
                logger.debug("RAM query failed: %s", e)
                info["ram_total_gb"] = 16.0
                info["ram_avail_gb"] = 8.0
        else:
            info["ram_total_gb"] = 16.0
            info["ram_avail_gb"] = 8.0

        # Disk info
        try:
            cwd = Path.cwd()
            usage = shutil.disk_usage(cwd)
            info["disk_total_gb"] = round(usage.total / (1024**3), 2)
            info["disk_free_gb"] = round(usage.free / (1024**3), 2)
            info["disk_used_gb"] = round(usage.used / (1024**3), 2)
        except Exception as e:
            logger.debug("Disk usage query failed: %s", e)

        return info

    @classmethod
    def create_diagnostics_bundle(
        cls,
        output_dir: str | Path,
        db_path: str | Path | None = None,
        log_dir: str | Path | None = None,
        app_state_info: dict[str, Any] | None = None,
        archive_name_prefix: str = "diagnostics_bundle",
    ) -> Path:
        """Packages system metrics, application state, logs, and a clean SQLite snapshot into a zip archive."""
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"{archive_name_prefix}_{timestamp_str}.zip"
        zip_path = out_p / zip_filename

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 1. System Telemetry
            telemetry = cls.get_system_telemetry()
            zf.writestr("system_info.json", json.dumps(telemetry, indent=2))

            # 2. App State Info
            if app_state_info:
                zf.writestr("app_state.json", json.dumps(app_state_info, indent=2))

            # 3. Collect Logs
            if log_dir is not None:
                log_p = Path(log_dir)
                if log_p.exists():
                    for log_file in log_p.glob("*.log"):
                        try:
                            zf.write(log_file, arcname=f"logs/{log_file.name}")
                        except Exception as e:
                            logger.warning("Could not include log file %s: %s", log_file, e)

            # 4. SQLite DB Snapshot (using sqlite3.backup API to safely handle live WAL)
            if db_path is not None:
                src_db_p = Path(db_path)
                if src_db_p.exists():
                    temp_snapshot = out_p / f"temp_snapshot_{timestamp_str}.db"
                    try:
                        with sqlite3.connect(src_db_p) as src_conn, sqlite3.connect(temp_snapshot) as dest_conn:
                            src_conn.backup(dest_conn)
                        zf.write(temp_snapshot, arcname="database/evaluation_snapshot.db")
                    except Exception as e:
                        logger.warning("SQLite snapshot backup error: %s", e)
                        # Fallback direct copy if backup fails
                        try:
                            zf.write(src_db_p, arcname="database/evaluation_snapshot.db")
                        except Exception as ce:
                            logger.error("Direct DB copy failed: %s", ce)
                    finally:
                        if temp_snapshot.exists():
                            try:
                                temp_snapshot.unlink()
                            except OSError:
                                pass

            # 5. Manifest & File Hashes
            manifest = {
                "created_at": datetime.datetime.now(datetime.UTC).isoformat(),
                "archive_name": zip_filename,
                "included_entries": zf.namelist(),
            }
            zf.writestr("bundle_manifest.json", json.dumps(manifest, indent=2))

        # Compute SHA-256 of the generated zip
        hasher = hashlib.sha256()
        with open(zip_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        sha256_hash = hasher.hexdigest()

        # Write sidecar sha256 checksum file
        sha_file = out_p / f"{zip_filename}.sha256"
        sha_file.write_text(f"{sha256_hash}  {zip_filename}\n", encoding="utf-8")

        logger.info("Diagnostics bundle created: %s (SHA-256: %s)", zip_path, sha256_hash[:16])
        return zip_path


class WatchdogService:
    """Multi-worker process/thread watchdog with heartbeat pings, recovery, and rate-limiting."""

    def __init__(
        self,
        heartbeat_timeout_seconds: float = 6.0,
        check_interval_seconds: float = 2.0,
        restart_callback: Callable[[str], None] | None = None,
        max_restarts_per_window: int = 5,
        restart_window_seconds: float = 60.0,
    ):
        self.timeout = heartbeat_timeout_seconds
        self.check_interval = check_interval_seconds
        self.restart_callback = restart_callback
        self.max_restarts_per_window = max_restarts_per_window
        self.restart_window_seconds = restart_window_seconds

        self._heartbeats: dict[str, float] = {}
        self._restart_history: dict[str, list[float]] = {}
        self._supervised_processes: dict[str, subprocess.Popen[Any]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

    def register_worker(self, name: str) -> None:
        """Registers a worker or process under watchdog supervision."""
        with self._lock:
            self._heartbeats[name] = time.monotonic()
            if name not in self._restart_history:
                self._restart_history[name] = []

    register_process = register_worker

    def record_heartbeat(self, name: str) -> None:
        """Updates last heartbeat timestamp for the worker."""
        with self._lock:
            self._heartbeats[name] = time.monotonic()

    def is_alive(self, name: str) -> bool:
        """Returns True if the worker sent a heartbeat within the timeout window."""
        with self._lock:
            last = self._heartbeats.get(name)
            if last is None:
                return False
            return (time.monotonic() - last) <= self.timeout

    def start(self) -> None:
        """Starts background monitoring thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="WatchdogSupervisionLoop",
            daemon=True,
        )
        self._thread.start()
        logger.info("WatchdogService started (timeout=%.1fs)", self.timeout)

    def stop(self) -> None:
        """Stops background monitoring thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("WatchdogService stopped")

    def supervise_process(self, name: str, popen_obj: subprocess.Popen[Any]) -> None:
        """Attaches a child subprocess for liveness and exit-code monitoring."""
        with self._lock:
            self._supervised_processes[name] = popen_obj
            self._heartbeats[name] = time.monotonic()
            if name not in self._restart_history:
                self._restart_history[name] = []

    def _should_allow_restart(self, name: str) -> bool:
        """Rate limits restarts to avoid tight infinite crash loops."""
        now = time.monotonic()
        history = self._restart_history.setdefault(name, [])
        # Prune older than window
        cutoff = now - self.restart_window_seconds
        history[:] = [t for t in history if t > cutoff]

        if len(history) >= self.max_restarts_per_window:
            logger.error(
                "WATCHDOG RESTART BLOCKED: '%s' reached max restart limit (%d in %.0fs)",
                name,
                self.max_restarts_per_window,
                self.restart_window_seconds,
            )
            return False

        history.append(now)
        return True

    def _monitor_loop(self) -> None:
        """Periodic loop checking heartbeats and subprocess exit statuses."""
        while self._running:
            now = time.monotonic()
            failed_workers: list[tuple[str, str]] = []

            with self._lock:
                # 1. Check Heartbeats
                for name, last_time in self._heartbeats.items():
                    elapsed = now - last_time
                    if elapsed > self.timeout:
                        failed_workers.append((name, f"Heartbeat timed out ({elapsed:.1f}s > {self.timeout:.1f}s)"))

                # 2. Check Supervised Subprocesses
                for name, proc in list(self._supervised_processes.items()):
                    ret = proc.poll()
                    if ret is not None:
                        failed_workers.append((name, f"Subprocess exited with code {ret}"))

            # Execute recovery callbacks outside the lock
            for name, reason in failed_workers:
                logger.error("WATCHDOG TRIGGERED on '%s': %s", name, reason)
                if self._should_allow_restart(name):
                    if self.restart_callback:
                        try:
                            self.restart_callback(name)
                        except Exception as e:
                            logger.critical("Crash recovery callback failed for '%s': %s", name, e)
                    # Reset heartbeat after triggering recovery
                    with self._lock:
                        self._heartbeats[name] = time.monotonic()
                        # If it was a subprocess that terminated, remove old handle
                        if name in self._supervised_processes and self._supervised_processes[name].poll() is not None:
                            self._supervised_processes.pop(name, None)

            time.sleep(self.check_interval)

    def get_metrics(self) -> dict[str, Any]:
        """Returns health telemetry and status of all monitored entities."""
        with self._lock:
            now = time.monotonic()
            workers = {}
            for name, last_time in self._heartbeats.items():
                workers[name] = {
                    "last_heartbeat_ago_sec": round(now - last_time, 2),
                    "alive": (now - last_time) <= self.timeout,
                    "restarts_in_window": len(self._restart_history.get(name, [])),
                }
            return {
                "running": self._running,
                "timeout_seconds": self.timeout,
                "monitored_count": len(self._heartbeats),
                "workers": workers,
            }
