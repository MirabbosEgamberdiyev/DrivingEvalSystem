"""Serial ELM327 OBD-II Reader Service.

Connects to vehicle OBD-II diagnostic port via ELM327 USB/Bluetooth adapter,
queries speed (PID 010D) and engine RPM (PID 010C), and produces OBDData.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from driving_eval.hardware.sensor_fusion import OBDData

logger = logging.getLogger("driving_eval.hardware.obd")


def parse_elm327_speed_response(response: str) -> float:
    """Parses response for PID 010D.

    Example response: '41 0D 2D' -> 0x2D = 45 km/h
    """
    try:
        clean = response.replace(" ", "").upper()
        if "410D" in clean:
            idx = clean.find("410D") + 4
            hex_val = clean[idx:idx + 2]
            return float(int(hex_val, 16))
    except Exception:
        pass
    return 0.0


def parse_elm327_rpm_response(response: str) -> int:
    """Parses response for PID 010C.

    Example response: '41 0C 1A F8' -> ((0x1A * 256) + 0xF8) / 4 = 1726 RPM
    """
    try:
        clean = response.replace(" ", "").upper()
        if "410C" in clean:
            idx = clean.find("410C") + 4
            hex_a = clean[idx:idx + 2]
            hex_b = clean[idx + 2:idx + 4]
            raw = (int(hex_a, 16) * 256) + int(hex_b, 16)
            return int(raw / 4)
    except Exception:
        pass
    return 0


class SerialOBDReader:
    """Queries vehicle speed and engine RPM via ELM327 OBD-II COM port."""

    def __init__(
        self,
        port: str = "COM4",
        baudrate: int = 38400,
        query_interval_seconds: float = 0.1,
        callback: Callable[[OBDData], None] | None = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.query_interval = query_interval_seconds
        self.callback = callback
        self._running = False
        self._thread: threading.Thread | None = None
        self.last_obd_data: OBDData | None = None

    def start(self) -> None:
        """Starts background thread polling OBD-II interface."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, name="SerialOBDWorker", daemon=True)
        self._thread.start()
        logger.info("Serial OBD-II Reader started on port %s (%d baud)", self.port, self.baudrate)

    def stop(self) -> None:
        """Stops background polling worker."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Serial OBD-II Reader stopped")

    def _init_elm327(self, ser: Any) -> bool:
        """Initializes ELM327 with AT commands."""
        commands = [
            b"ATZ\r",       # Reset
            b"ATE0\r",      # Echo off
            b"ATL0\r",      # Linefeeds off
            b"ATH0\r",      # Headers off
            b"ATSP0\r",     # Set protocol auto
        ]
        for cmd in commands:
            ser.write(cmd)
            time.sleep(0.1)
            ser.read(ser.in_waiting or 1)
        return True

    def _poll_loop(self) -> None:
        """Main query loop requesting speed and RPM."""
        while self._running:
            ser: Any = None
            try:
                import serial
                ser = serial.Serial(self.port, self.baudrate, timeout=0.2)
                self._init_elm327(ser)
                logger.info("Connected to ELM327 OBD-II adapter on %s", self.port)

                while self._running:
                    # Query Speed
                    ser.write(b"010D\r")
                    time.sleep(0.04)
                    speed_resp = ser.read(ser.in_waiting or 32).decode("ascii", errors="replace")
                    speed_kmh = parse_elm327_speed_response(speed_resp)

                    # Query RPM
                    ser.write(b"010C\r")
                    time.sleep(0.04)
                    rpm_resp = ser.read(ser.in_waiting or 32).decode("ascii", errors="replace")
                    rpm = parse_elm327_rpm_response(rpm_resp)

                    obd_data = OBDData(
                        speed_kmh=speed_kmh,
                        engine_rpm=rpm,
                        seatbelt_fastened=True,  # Default True unless sensor triggered
                        handbrake_active=False,
                        turn_signal_left=False,
                        turn_signal_right=False,
                        timestamp=time.time(),
                    )
                    self.last_obd_data = obd_data
                    if self.callback:
                        self.callback(obd_data)

                    time.sleep(self.query_interval)

            except Exception as e:
                logger.debug("OBD-II serial connection retry on %s: %s", self.port, e)
                time.sleep(2.0)
            finally:
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:
                        pass
