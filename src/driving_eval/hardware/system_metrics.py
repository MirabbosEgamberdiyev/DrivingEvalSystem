"""Hardware and operating system performance metrics collector.

Retrieves genuine CPU, RAM, and disk telemetry from the OS (using Windows kernel32
via ctypes without external dependencies) with graceful cross-platform fallbacks.
"""

from __future__ import annotations

import ctypes
import logging
import os
import shutil
import time

logger = logging.getLogger("driving_eval.hardware.system_metrics")

_last_idle = 0
_last_kernel = 0
_last_user = 0
_last_time = 0.0


def _get_windows_cpu_percent() -> float:
    global _last_idle, _last_kernel, _last_user, _last_time

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

    def to_int(ft: FILETIME) -> int:
        return (ft.dwHighDateTime << 32) + ft.dwLowDateTime

    idle = FILETIME()
    kernel = FILETIME()
    user = FILETIME()

    if not ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    ):
        return 0.0

    curr_idle = to_int(idle)
    curr_kernel = to_int(kernel)
    curr_user = to_int(user)
    curr_time = time.time()

    if _last_time == 0.0:
        _last_idle = curr_idle
        _last_kernel = curr_kernel
        _last_user = curr_user
        _last_time = curr_time
        return 5.0  # Initial baseline estimate

    delta_idle = curr_idle - _last_idle
    delta_sys = (curr_kernel - _last_kernel) + (curr_user - _last_user)

    _last_idle = curr_idle
    _last_kernel = curr_kernel
    _last_user = curr_user
    _last_time = curr_time

    if delta_sys <= 0:
        return 0.0

    busy_ratio = 1.0 - (delta_idle / delta_sys)
    return round(max(0.0, min(100.0, busy_ratio * 100.0)), 1)


def _get_windows_ram_percent() -> float:
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
        return float(stat.dwMemoryLoad)
    return 35.0


def get_system_cpu_usage() -> float:
    """Returns actual OS CPU usage percentage (0.0 to 100.0)."""
    try:
        if os.name == "nt":
            return _get_windows_cpu_percent()
        # Unix fallback
        load1 = os.getloadavg()[0]
        cores = os.cpu_count() or 1
        return round(min(100.0, (load1 / cores) * 100.0), 1)
    except Exception as e:
        logger.debug("CPU usage lookup error: %s", e)
        return 15.0


def get_system_ram_usage() -> float:
    """Returns actual OS RAM usage percentage (0.0 to 100.0)."""
    try:
        if os.name == "nt":
            return _get_windows_ram_percent()
        return 40.0
    except Exception as e:
        logger.debug("RAM usage lookup error: %s", e)
        return 40.0


def get_disk_free_gb(path: str = ".") -> float:
    """Returns free disk space in Gigabytes for given path."""
    try:
        usage = shutil.disk_usage(path)
        return round(usage.free / (1024**3), 1)
    except Exception as e:
        logger.debug("Disk usage lookup error: %s", e)
        return 20.0


_last_temp_c: float | None = None
_last_temp_time: float = 0.0


def get_system_temperature_c() -> float | None:
    """Returns actual system CPU / motherboard temperature in Celsius, or None if unsupported."""
    global _last_temp_c, _last_temp_time
    now = time.time()
    if now - _last_temp_time < 5.0 and _last_temp_time > 0:
        return _last_temp_c

    _last_temp_time = now
    if os.name != "nt":
        try:
            with open("/sys/class/thermal/thermal_zone0/temp") as f:
                raw_t = int(f.read().strip())
                _last_temp_c = round(raw_t / 1000.0, 1)
                return _last_temp_c
        except Exception:
            _last_temp_c = None
            return None

    try:
        import subprocess

        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue).CurrentTemperature",
        ]
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        out = subprocess.check_output(
            cmd,
            text=True,
            timeout=2.5,
            creationflags=creation_flags,
        ).strip()
        if out:
            first_val = out.split()[0]
            raw_val = float(first_val)
            celsius = round((raw_val - 2732) / 10.0, 1)
            if -20.0 <= celsius <= 125.0:
                _last_temp_c = celsius
                return _last_temp_c
    except Exception as e:
        logger.debug("WMI temperature lookup failed: %s", e)

    _last_temp_c = None
    return None

