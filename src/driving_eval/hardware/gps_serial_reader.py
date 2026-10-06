"""Serial NMEA GPS Reader Service.

Reads live telemetry from USB/UART GPS receivers (e.g. u-blox Neo-6M/Neo-8M),
parses standard NMEA 0183 sentences ($GPRMC, $GPGGA), and feeds GPSData into SensorFusion.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

from driving_eval.hardware.sensor_fusion import GPSData

logger = logging.getLogger("driving_eval.hardware.gps")


def parse_nmea_rmc(line: str) -> GPSData | None:
    """Parses $GPRMC / $GNRMC sentence.

    Format: $GPRMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,,,a*hh
    """
    try:
        parts = line.strip().split(",")
        if len(parts) < 9 or not (parts[0].endswith("RMC")):
            return None

        status = parts[2]
        fix_valid = (status == "A")  # A = Active / Valid, V = Void

        if not fix_valid or not parts[3] or not parts[5]:
            return GPSData(
                lat=0.0,
                lon=0.0,
                speed_kmh=0.0,
                heading_deg=0.0,
                fix_valid=False,
                timestamp=time.time(),
            )

        # Parse Latitude (ddmm.mmmm)
        raw_lat = float(parts[3])
        lat_deg = int(raw_lat / 100)
        lat_min = raw_lat - (lat_deg * 100)
        lat = lat_deg + (lat_min / 60.0)
        if parts[4] == "S":
            lat = -lat

        # Parse Longitude (dddmm.mmmm)
        raw_lon = float(parts[5])
        lon_deg = int(raw_lon / 100)
        lon_min = raw_lon - (lon_deg * 100)
        lon = lon_deg + (lon_min / 60.0)
        if parts[6] == "W":
            lon = -lon

        # Speed in knots -> km/h (1 knot = 1.852 km/h)
        speed_knots = float(parts[7]) if parts[7] else 0.0
        speed_kmh = round(speed_knots * 1.852, 2)

        # Heading in degrees
        heading_deg = float(parts[8]) if parts[8] else 0.0

        return GPSData(
            lat=lat,
            lon=lon,
            speed_kmh=speed_kmh,
            heading_deg=heading_deg,
            fix_valid=True,
            timestamp=time.time(),
        )
    except Exception as e:
        logger.debug("Failed parsing NMEA RMC sentence '%s': %s", line, e)
        return None


class SerialGPSReader:
    """Monitors USB COM port for NMEA GPS receiver and emits GPSData updates."""

    def __init__(
        self,
        port: str = "COM3",
        baudrate: int = 9600,
        callback: Callable[[GPSData], None] | None = None,
    ):
        self.port = port
        self.baudrate = baudrate
        self.callback = callback
        self._running = False
        self._thread: threading.Thread | None = None
        self.last_gps_data: GPSData | None = None

    def start(self) -> None:
        """Starts background thread reading serial COM port."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, name="SerialGPSWorker", daemon=True)
        self._thread.start()
        logger.info("Serial GPS Reader started on port %s (%d baud)", self.port, self.baudrate)

    def stop(self) -> None:
        """Stops background serial worker."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        logger.info("Serial GPS Reader stopped")

    def _read_loop(self) -> None:
        """Loop maintaining connection to serial port and reading lines."""
        while self._running:
            ser: Any = None
            try:
                import serial
                ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
                logger.info("Connected to GPS receiver on %s", self.port)

                while self._running:
                    line_bytes = ser.readline()
                    if not line_bytes:
                        continue
                    line_str = line_bytes.decode("ascii", errors="replace").strip()
                    if line_str.startswith("$"):
                        gps_data = parse_nmea_rmc(line_str)
                        if gps_data is not None:
                            self.last_gps_data = gps_data
                            if self.callback:
                                self.callback(gps_data)

            except Exception as e:
                logger.debug("GPS serial connection retry on %s: %s", self.port, e)
                time.sleep(2.0)  # Wait before reconnection attempt
            finally:
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:
                        pass
