"""Multi-camera acquisition service for 4-camera offline driving evaluation.

Provides synchronized frame bundles with monotonic timestamps, health monitoring,
automatic reconnection, and simulated video feeds.
"""

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import cv2
import numpy as np

from driving_eval.core.config_schema import CameraDeviceConfig, CamerasConfig

logger = logging.getLogger("driving_eval.hardware.camera")


class StreamStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    RECONNECTING = "RECONNECTING"
    DEGRADED = "DEGRADED"


@dataclass
class CameraFrame:
    camera_name: str
    frame: np.ndarray
    timestamp: float  # time.monotonic()
    frame_index: int
    resolution: tuple[int, int]  # (w, h)


@dataclass
class FrameBundle:
    timestamp: float
    frames: dict[str, CameraFrame]
    is_synchronized: bool
    max_jitter_ms: float


@dataclass
class CameraHealth:
    name: str
    status: StreamStatus
    fps: float
    dropped_frames: int
    total_frames: int
    last_frame_timestamp: float
    sharpness_score: float  # Variance of Laplacian


class SingleCameraWorker:
    """Independent worker thread capturing from one camera device or simulated video."""

    def __init__(self, config: CameraDeviceConfig, simulation_mode: bool = False):
        self.config = config
        self.simulation_mode = simulation_mode
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

        self._latest_frame: CameraFrame | None = None
        self._cap: cv2.VideoCapture | None = None
        self._frame_counter: int = 0
        self._dropped_counter: int = 0

        # Health metrics
        self._fps: float = 0.0
        self._fps_counter: int = 0
        self._last_fps_calc_time = time.monotonic()
        self._last_frame_time = time.monotonic()
        self._sharpness: float = 100.0
        self._status = StreamStatus.OFFLINE

    @property
    def status(self) -> StreamStatus:
        return self._status

    def get_health(self) -> CameraHealth:
        with self._lock:
            return CameraHealth(
                name=self.config.name,
                status=self._status,
                fps=round(self._fps, 1),
                dropped_frames=self._dropped_counter,
                total_frames=self._frame_counter,
                last_frame_timestamp=self._last_frame_time,
                sharpness_score=round(self._sharpness, 1),
            )

    def get_latest_frame(self) -> CameraFrame | None:
        with self._lock:
            return self._latest_frame

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._capture_loop, name=f"CamWorker-{self.config.name}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()
            self._cap = None
        self._status = StreamStatus.OFFLINE

    def _open_capture(self) -> bool:
        if self.simulation_mode:
            path = Path(self.config.sim_video_path)
            if path.exists():
                self._cap = cv2.VideoCapture(str(path))
                if self._cap.isOpened():
                    self._status = StreamStatus.ONLINE
                    return True
            # Fallback for simulation: procedural generator
            self._status = StreamStatus.ONLINE
            return True
        else:
            uri = self.config.stream_uri
            if uri:
                self._cap = cv2.VideoCapture(uri, cv2.CAP_FFMPEG)
                if self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                # Local USB camera device index: prefer DirectShow on Windows for fast init
                device_idx = self.config.device_index
                try:
                    self._cap = cv2.VideoCapture(device_idx, cv2.CAP_DSHOW)
                    if not self._cap.isOpened():
                        self._cap = cv2.VideoCapture(device_idx)
                except Exception:
                    self._cap = cv2.VideoCapture(device_idx)

            if self._cap and self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
                self._cap.set(cv2.CAP_PROP_FPS, self.config.fps)
                self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self._status = StreamStatus.ONLINE
                return True
            else:
                self._status = StreamStatus.OFFLINE
                return False

    def _generate_synthetic_frame(self) -> np.ndarray:
        """Generates synthetic frame when no hardware camera or file is available."""
        img = np.zeros((self.config.height, self.config.width, 3), dtype=np.uint8)
        # Gradient background
        img[:, :] = (30, 35, 40)
        # Draw road lanes
        cv2.line(img, (200, self.config.height), (self.config.width // 2 - 50, 300), (200, 200, 200), 4)
        cv2.line(img, (self.config.width - 200, self.config.height), (self.config.width // 2 + 50, 300), (200, 200, 200), 4)
        # Info overlay
        text = f"CAM: {self.config.name} | Frame #{self._frame_counter}"
        cv2.putText(img, text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        return img

    def _calculate_sharpness(self, frame: np.ndarray) -> float:
        """Calculates image sharpness using the variance of the Laplacian."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def _capture_loop(self) -> None:
        self._status = StreamStatus.RECONNECTING
        if not self._open_capture():
            logger.warning("Kamera %s ochilmadi, qayta ulanish rejimida.", self.config.name)

        frame_duration = 1.0 / self.config.fps

        while self._running:
            loop_start = time.monotonic()
            frame_img: np.ndarray | None = None

            if self._cap and self._cap.isOpened():
                ret, raw_frame = self._cap.read()
                if ret and raw_frame is not None:
                    frame_img = raw_frame
                else:
                    # Video ended in sim mode: rewind
                    if self.simulation_mode:
                        self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, raw_frame = self._cap.read()
                        if ret:
                            frame_img = raw_frame
                    else:
                        self._dropped_counter += 1
                        self._status = StreamStatus.DEGRADED
            elif self.simulation_mode:
                # Procedural fallback
                frame_img = self._generate_synthetic_frame()

            if frame_img is not None:
                self._frame_counter += 1
                now = time.monotonic()
                self._last_frame_time = now
                self._fps_counter += 1

                # Sharpness check every 15 frames
                if self._frame_counter % 15 == 0:
                    self._sharpness = self._calculate_sharpness(frame_img)

                # FPS calculation
                elapsed_fps = now - self._last_fps_calc_time
                if elapsed_fps >= 1.0:
                    self._fps = self._fps_counter / elapsed_fps
                    self._fps_counter = 0
                    self._last_fps_calc_time = now

                cam_frame = CameraFrame(
                    camera_name=self.config.name,
                    frame=frame_img,
                    timestamp=now,
                    frame_index=self._frame_counter,
                    resolution=(frame_img.shape[1], frame_img.shape[0]),
                )
                with self._lock:
                    self._latest_frame = cam_frame
                    self._status = StreamStatus.ONLINE

            elapsed = time.monotonic() - loop_start
            sleep_time = max(0.001, frame_duration - elapsed)
            time.sleep(sleep_time)


class MultiCameraService:
    """Manages all 4 synchronized camera streams with health checks and synchronization."""

    def __init__(self, config: CamerasConfig, simulation_mode: bool = False):
        self.config = config
        self.simulation_mode = simulation_mode
        self.workers: dict[str, SingleCameraWorker] = {}

        for key, dev_cfg in self.config.devices.items():
            self.workers[dev_cfg.name] = SingleCameraWorker(dev_cfg, simulation_mode=simulation_mode)

    def start_all(self) -> None:
        """Starts all camera acquisition threads."""
        for worker in self.workers.values():
            worker.start()

    def stop_all(self) -> None:
        """Stops all camera acquisition threads."""
        for worker in self.workers.values():
            worker.stop()

    def get_synchronized_bundle(self) -> FrameBundle | None:
        """Collects the latest frames from all 4 cameras and checks sync tolerance."""
        frames: dict[str, CameraFrame] = {}
        timestamps: list[float] = []

        for name, worker in self.workers.items():
            f = worker.get_latest_frame()
            if f is not None:
                frames[name] = f
                timestamps.append(f.timestamp)

        if len(frames) < len(self.workers):
            # Not all cameras have delivered a frame yet
            return None

        min_ts = min(timestamps)
        max_ts = max(timestamps)
        jitter_ms = (max_ts - min_ts) * 1000.0
        is_synced = jitter_ms <= self.config.sync_tolerance_ms

        return FrameBundle(
            timestamp=max_ts,
            frames=frames,
            is_synchronized=is_synced,
            max_jitter_ms=round(jitter_ms, 2),
        )

    def get_all_health(self) -> dict[str, CameraHealth]:
        """Returns health metrics for all 4 cameras."""
        return {name: worker.get_health() for name, worker in self.workers.items()}
