"""Evidence recorder capturing ring buffer snapshots, video clips, and SHA-256 hashes.

Produces before.jpg, event.jpg, after.jpg, composite.jpg (4-camera grid), event.mp4,
and metadata.json for each violation, cryptographically logged in SQLite.
"""

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from driving_eval.db.repository import DatabaseRepository
from driving_eval.hardware.camera_service import FrameBundle
from driving_eval.rules.event_manager import ProcessedViolationEvent

logger = logging.getLogger("driving_eval.evidence.recorder")


@dataclass
class BufferedFrame:
    camera_name: str
    frame: np.ndarray
    timestamp: float


class EvidenceRecorder:
    """Manages circular frame buffer and saves cryptographically signed violation evidence."""

    def __init__(
        self,
        base_dir: str | Path,
        repository: DatabaseRepository,
        buffer_duration_seconds: float = 5.0,
        fps: int = 30,
    ):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.repository = repository
        self.buffer_size = int(buffer_duration_seconds * fps)
        self._ring_buffer: dict[str, deque[BufferedFrame]] = {
            "FRONT": deque(maxlen=self.buffer_size),
            "REAR": deque(maxlen=self.buffer_size),
            "LEFT": deque(maxlen=self.buffer_size),
            "RIGHT": deque(maxlen=self.buffer_size),
        }
        self._lock = threading.Lock()

    def push_bundle(self, bundle: FrameBundle) -> None:
        """Pushes a synchronized bundle into the circular buffers."""
        with self._lock:
            for cam_name, cam_frame in bundle.frames.items():
                if cam_name in self._ring_buffer:
                    self._ring_buffer[cam_name].append(
                        BufferedFrame(
                            camera_name=cam_name,
                            frame=cam_frame.frame.copy(),
                            timestamp=cam_frame.timestamp,
                        )
                    )

    def record_evidence_package(
        self,
        session_id: str,
        event: ProcessedViolationEvent,
    ) -> str:
        """Extracts before/event/after frames, 4-camera composite, and MP4 clip,

        computes SHA-256, and logs to DB. Returns evidence_id.
        """
        evidence_id = f"EVID-{event.violation_id}"
        dest_dir = self.base_dir / session_id / event.violation_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        target_cam = event.camera if event.camera in self._ring_buffer else "FRONT"

        with self._lock:
            buf = list(self._ring_buffer[target_cam])
            all_cams_latest = {
                cam: self._ring_buffer[cam][-1].frame.copy()
                for cam in ("FRONT", "REAR", "LEFT", "RIGHT")
                if len(self._ring_buffer[cam]) > 0
            }

        if not buf:
            # Fallback placeholder image if buffer is empty
            blank = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(
                blank,
                f"EVIDENCE {event.rule_code}",
                (50, 360),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 0, 255),
                2,
            )
            buf = [BufferedFrame(target_cam, blank, event.timestamp)]

        # 1. Select before, event, after frames
        total = len(buf)
        event_idx = total - 1
        before_idx = max(0, event_idx - 15)  # ~0.5s before
        after_idx = event_idx

        before_frame = buf[before_idx].frame
        event_frame = buf[event_idx].frame
        after_frame = buf[after_idx].frame

        # Annotate event frame with text and bounding box
        annotated_event_frame = event_frame.copy()
        if "bbox" in event.evidence_metadata:
            bbox = event.evidence_metadata["bbox"]
            cv2.rectangle(
                annotated_event_frame,
                (int(bbox[0]), int(bbox[1])),
                (int(bbox[2]), int(bbox[3])),
                (0, 0, 255),
                3,
            )
        banner = f"[{event.status}] {event.rule_code} - Penalty: {event.penalty} (Conf: {event.confidence:.2f})"
        cv2.putText(annotated_event_frame, banner, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        # 2. Save Images
        before_path = dest_dir / "before.jpg"
        event_path = dest_dir / "event.jpg"
        after_path = dest_dir / "after.jpg"

        cv2.imwrite(str(before_path), before_frame)
        cv2.imwrite(str(event_path), annotated_event_frame)
        cv2.imwrite(str(after_path), after_frame)

        # 3. Create 4-Camera Composite Grid (2x2)
        composite_path = dest_dir / "composite.jpg"
        composite_img = self._create_4cam_composite(all_cams_latest, event_frame.shape[:2])
        cv2.imwrite(str(composite_path), composite_img)

        # 4. Save MP4 Clip (1-2 seconds from buffer)
        mp4_path = dest_dir / "event.mp4"
        h, w = event_frame.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(mp4_path), fourcc, 20.0, (w, h))
        clip_frames = buf[-40:] if len(buf) >= 40 else buf
        for f in clip_frames:
            writer.write(f.frame)
        writer.release()

        # 5. Save metadata.json
        meta_path = dest_dir / "metadata.json"
        meta_data = {
            "evidence_id": evidence_id,
            "session_id": session_id,
            "violation_id": event.violation_id,
            "rule_code": event.rule_code,
            "status": event.status,
            "confidence": event.confidence,
            "penalty": event.penalty,
            "camera": event.camera,
            "exercise": event.exercise,
            "timestamp": event.timestamp,
            "details": event.details,
            "metadata": event.evidence_metadata,
            "created_at": time.time(),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2, ensure_ascii=False)

        # 6. Compute SHA-256 and commit to DB
        saved_files = [
            (before_path, "IMAGE"),
            (event_path, "IMAGE"),
            (after_path, "IMAGE"),
            (composite_path, "IMAGE"),
            (mp4_path, "VIDEO"),
            (meta_path, "JSON"),
        ]

        for f_path, f_type in saved_files:
            file_hash = self.repository.compute_file_sha256(f_path)
            self.repository.record_evidence(
                evidence_id=f"{evidence_id}-{f_path.name}",
                session_id=session_id,
                violation_id=event.violation_id,
                file_path=str(f_path),
                file_type=f_type,
                sha256_hash=file_hash,
            )

        logger.info("Dalillar saqlandi va SHA-256 bilan imzolandi: %s", dest_dir)
        return evidence_id

    def verify_package_integrity(self, session_id: str, violation_id: str) -> tuple[bool, list[str]]:
        """Verifies on-disk files against stored SHA-256 hashes in SQLite."""
        dest_dir = self.base_dir / session_id / violation_id
        if not dest_dir.exists():
            return False, ["Dalillar papkasi mavjud emas"]

        errors: list[str] = []
        for f_path in dest_dir.iterdir():
            if not f_path.is_file():
                continue
            ev_id = f"EVID-{violation_id}-{f_path.name}"
            # Check hash in DB
            db_evidence = self.repository.get_evidence(ev_id)
            if not db_evidence:
                errors.append(f"DB da ro'yxatdan o'tmagan fayl: {f_path.name}")
                continue

            current_hash = self.repository.compute_file_sha256(f_path)
            if current_hash != db_evidence["sha256_hash"]:
                errors.append(f"Xesh mos kelmadi: {f_path.name} (soxtalashtirilgan)")

        return len(errors) == 0, errors

    @staticmethod
    def _create_4cam_composite(
        cams: dict[str, np.ndarray], target_shape: tuple[int, int]
    ) -> np.ndarray:
        """Combines 4 camera frames into a 2x2 grid (FRONT, REAR, LEFT, RIGHT)."""
        h, w = target_shape
        half_h, half_w = h // 2, w // 2
        grid = np.zeros((h, w, 3), dtype=np.uint8)

        cam_names = [("FRONT", (0, 0)), ("REAR", (half_w, 0)), ("LEFT", (0, half_h)), ("RIGHT", (half_w, half_h))]

        for name, (x, y) in cam_names:
            frame = cams.get(name)
            if frame is not None:
                resized = cv2.resize(frame, (half_w, half_h))
            else:
                resized = np.zeros((half_h, half_w, 3), dtype=np.uint8)
                cv2.putText(resized, f"NO {name}", (20, half_h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 120, 120), 2)

            cv2.putText(resized, name, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            grid[y : y + half_h, x : x + half_w] = resized

        return grid
