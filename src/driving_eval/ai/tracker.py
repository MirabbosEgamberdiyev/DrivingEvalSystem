"""ByteTrack Multi-Object Tracker for stable tracking of cones, lines, and obstacles.

Associates detections across consecutive frames to maintain consistent track IDs,
which is critical for debounce, anti-flicker, and duplicate violation prevention.
Implements the 2-stage association algorithm of ByteTrack:
1. High-confidence detections matched with active tracks.
2. Low-confidence detections matched with unmatched tracks to prevent ID switching
   during motion blur, partial occlusion, or sensor noise.
3. EMA bounding-box coordinate smoothing to eliminate jitter.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from driving_eval.ai.detector_base import BoundingBox, Detection


def calculate_iou(box1: BoundingBox, box2: BoundingBox) -> float:
    """Calculates Intersection over Union (IoU) between two bounding boxes."""
    inter_x1 = max(box1.x1, box2.x1)
    inter_y1 = max(box1.y1, box2.y1)
    inter_x2 = min(box1.x2, box2.x2)
    inter_y2 = min(box1.y2, box2.y2)

    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area1 = box1.width * box1.height
    area2 = box2.width * box2.height
    union_area = area1 + area2 - inter_area

    if union_area <= 0.0:
        return 0.0
    return inter_area / union_area


class TrackState(str, Enum):
    """Lifecycle state of a tracked object."""
    TENTATIVE = "TENTATIVE"    # Seen 1 to min_hits-1 times, not yet confirmed
    CONFIRMED = "CONFIRMED"    # Confirmed track, raises valid violations
    LOST = "LOST"              # Temporarily invisible, awaiting re-identification
    REMOVED = "REMOVED"        # Pruned after max_invisible_frames


@dataclass
class TrackedObject:
    """Internal state representation of an active track."""
    track_id: int
    label: str
    camera: str
    bbox: BoundingBox
    confidence: float
    first_seen_timestamp: float
    last_seen_timestamp: float
    hits: int
    age: int
    consecutive_invisible: int
    state: TrackState = TrackState.TENTATIVE
    vx: float = 0.0  # Velocity x in px/s
    vy: float = 0.0  # Velocity y in px/s
    history: list[BoundingBox] = field(default_factory=list)

    def predict_bbox(self, dt: float) -> BoundingBox:
        """Predicts expected bounding box based on velocity."""
        if dt <= 0.0 or dt > 0.5:
            return self.bbox
        dx = self.vx * dt
        dy = self.vy * dt
        return BoundingBox(
            x1=self.bbox.x1 + dx,
            y1=self.bbox.y1 + dy,
            x2=self.bbox.x2 + dx,
            y2=self.bbox.y2 + dy,
        )


class SimpleByteTracker:
    """ByteTrack 2-stage multi-object tracker with bounding-box smoothing."""

    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_invisible_frames: int = 15,
        min_hits_to_confirm: int = 2,
        high_threshold: float = 0.5,
        low_threshold: float = 0.1,
        smooth_alpha: float = 0.75,
    ):
        self.iou_threshold = iou_threshold
        self.max_invisible_frames = max_invisible_frames
        self.min_hits_to_confirm = min_hits_to_confirm
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.smooth_alpha = smooth_alpha

        self._next_id: int = 1
        self._tracks: dict[int, TrackedObject] = {}
        self._last_timestamp: float | None = None

    @property
    def active_tracks(self) -> dict[int, TrackedObject]:
        return dict(self._tracks)

    def is_confirmed(self, track_id: int) -> bool:
        """Returns True if track is confirmed and reliable for violation scoring."""
        tr = self._tracks.get(track_id)
        return tr is not None and tr.state == TrackState.CONFIRMED

    def update(self, detections: Sequence[Detection], timestamp: float) -> list[Detection]:
        """Updates tracks with detections using ByteTrack 2-stage association.

        Stage 1: Match high-confidence detections with active tracks.
        Stage 2: Match remaining low-confidence detections with unmatched tracks.
        Stage 3: Initialize new tentative tracks from remaining high-confidence detections.
        """
        dt = (timestamp - self._last_timestamp) if self._last_timestamp is not None else 0.033
        self._last_timestamp = timestamp

        # Partition detections into high and low confidence groups
        high_dets: list[Detection] = []
        low_dets: list[Detection] = []

        for d in detections:
            if d.confidence >= self.high_threshold:
                high_dets.append(d)
            elif d.confidence >= self.low_threshold:
                low_dets.append(d)

        matched_track_ids: set[int] = set()
        updated_detections: list[Detection] = []

        # ---------------------------------------------------------
        # STAGE 1: Match high-confidence detections with tracks
        # ---------------------------------------------------------
        unmatched_high_dets: list[Detection] = []
        sorted_high = sorted(high_dets, key=lambda d: d.confidence, reverse=True)

        for det in sorted_high:
            best_track_id, best_iou = self._find_best_match(det, matched_track_ids, dt)

            if best_track_id is not None and best_iou >= self.iou_threshold:
                matched_track_ids.add(best_track_id)
                self._update_track(best_track_id, det, timestamp, dt)
                det.track_id = best_track_id
                det.metadata["track_state"] = self._tracks[best_track_id].state.value
                det.metadata["is_confirmed"] = (self._tracks[best_track_id].state == TrackState.CONFIRMED)
                updated_detections.append(det)
            else:
                unmatched_high_dets.append(det)

        # ---------------------------------------------------------
        # STAGE 2: Match low-confidence detections with remaining tracks
        # (Preserves tracks during occlusion, motion blur, and low score dips)
        # ---------------------------------------------------------
        remaining_track_ids = set(self._tracks.keys()) - matched_track_ids
        for det in low_dets:
            best_track_id, best_iou = self._find_best_match_in_pool(
                det, remaining_track_ids, dt
            )
            if best_track_id is not None and best_iou >= self.iou_threshold:
                matched_track_ids.add(best_track_id)
                remaining_track_ids.remove(best_track_id)
                self._update_track(best_track_id, det, timestamp, dt)
                det.track_id = best_track_id
                det.metadata["track_state"] = self._tracks[best_track_id].state.value
                det.metadata["is_confirmed"] = (self._tracks[best_track_id].state == TrackState.CONFIRMED)
                updated_detections.append(det)

        # ---------------------------------------------------------
        # STAGE 3: Initialize new tracks for unmatched high-confidence detections
        # ---------------------------------------------------------
        new_track_ids: set[int] = set()
        for det in unmatched_high_dets:
            new_id = self._next_id
            self._next_id += 1
            initial_state = (
                TrackState.CONFIRMED if self.min_hits_to_confirm <= 1 else TrackState.TENTATIVE
            )
            new_track = TrackedObject(
                track_id=new_id,
                label=det.label,
                camera=det.camera,
                bbox=det.bbox,
                confidence=det.confidence,
                first_seen_timestamp=timestamp,
                last_seen_timestamp=timestamp,
                hits=1,
                age=1,
                consecutive_invisible=0,
                state=initial_state,
                history=[det.bbox],
            )
            self._tracks[new_id] = new_track
            new_track_ids.add(new_id)
            det.track_id = new_id
            det.metadata["track_state"] = initial_state.value
            det.metadata["is_confirmed"] = (initial_state == TrackState.CONFIRMED)
            updated_detections.append(det)

        # ---------------------------------------------------------
        # Manage invisible and dead tracks (excluding newly initialized tracks)
        # ---------------------------------------------------------
        dead_tracks = []
        for t_id, tr in self._tracks.items():
            if t_id not in matched_track_ids and t_id not in new_track_ids:
                tr.consecutive_invisible += 1
                tr.state = TrackState.LOST
                if tr.consecutive_invisible > self.max_invisible_frames:
                    dead_tracks.append(t_id)

        for t_id in dead_tracks:
            del self._tracks[t_id]

        return updated_detections

    def _find_best_match(
        self, det: Detection, matched_ids: set[int], dt: float
    ) -> tuple[int | None, float]:
        best_iou = 0.0
        best_track_id: int | None = None
        for t_id, track in self._tracks.items():
            if t_id in matched_ids or track.camera != det.camera:
                continue
            pred_box = track.predict_bbox(dt)
            iou = calculate_iou(pred_box, det.bbox)
            if iou > best_iou:
                best_iou = iou
                best_track_id = t_id
        return best_track_id, best_iou

    def _find_best_match_in_pool(
        self, det: Detection, candidate_ids: set[int], dt: float
    ) -> tuple[int | None, float]:
        best_iou = 0.0
        best_track_id: int | None = None
        for t_id in candidate_ids:
            track = self._tracks[t_id]
            if track.camera != det.camera:
                continue
            pred_box = track.predict_bbox(dt)
            iou = calculate_iou(pred_box, det.bbox)
            if iou > best_iou:
                best_iou = iou
                best_track_id = t_id
        return best_track_id, best_iou

    def _update_track(self, track_id: int, det: Detection, timestamp: float, dt: float) -> None:
        tr = self._tracks[track_id]

        # Calculate instantaneous velocity from previous bbox center
        if dt > 0.001:
            prev_cx, prev_cy = tr.bbox.center
            curr_cx, curr_cy = det.bbox.center
            inst_vx = (curr_cx - prev_cx) / dt
            inst_vy = (curr_cy - prev_cy) / dt
            tr.vx = 0.5 * tr.vx + 0.5 * inst_vx
            tr.vy = 0.5 * tr.vy + 0.5 * inst_vy

        # Exponential Moving Average (EMA) coordinate smoothing to eliminate jitter
        alpha = self.smooth_alpha
        smoothed_box = BoundingBox(
            x1=alpha * det.bbox.x1 + (1.0 - alpha) * tr.bbox.x1,
            y1=alpha * det.bbox.y1 + (1.0 - alpha) * tr.bbox.y1,
            x2=alpha * det.bbox.x2 + (1.0 - alpha) * tr.bbox.x2,
            y2=alpha * det.bbox.y2 + (1.0 - alpha) * tr.bbox.y2,
        )

        tr.bbox = smoothed_box
        det.bbox = smoothed_box
        tr.confidence = det.confidence
        tr.last_seen_timestamp = timestamp
        tr.hits += 1
        tr.age += 1
        tr.consecutive_invisible = 0

        # Promote tentative track to confirmed
        if tr.hits >= self.min_hits_to_confirm and tr.state == TrackState.TENTATIVE:
            tr.state = TrackState.CONFIRMED

        tr.history.append(smoothed_box)
        if len(tr.history) > 30:
            tr.history.pop(0)


# ByteTracker alias for full semantic parity
ByteTracker = SimpleByteTracker


class MultiCameraTracker:
    """Manages independent ByteTrack instances across 4 cameras (FRONT, REAR, LEFT, RIGHT)."""

    def __init__(
        self,
        cameras: Sequence[str] = ("FRONT", "REAR", "LEFT", "RIGHT"),
        iou_threshold: float = 0.3,
        max_invisible_frames: int = 15,
        min_hits_to_confirm: int = 2,
    ):
        self._trackers: dict[str, SimpleByteTracker] = {
            cam: SimpleByteTracker(
                iou_threshold=iou_threshold,
                max_invisible_frames=max_invisible_frames,
                min_hits_to_confirm=min_hits_to_confirm,
            )
            for cam in cameras
        }

    def update_camera(
        self, camera_name: str, detections: Sequence[Detection], timestamp: float
    ) -> list[Detection]:
        tracker = self._trackers.get(camera_name)
        if not tracker:
            tracker = SimpleByteTracker()
            self._trackers[camera_name] = tracker
        return tracker.update(detections, timestamp)

    def update_all(
        self, detections_by_camera: dict[str, Sequence[Detection]], timestamp: float
    ) -> dict[str, list[Detection]]:
        results: dict[str, list[Detection]] = {}
        for cam, dets in detections_by_camera.items():
            results[cam] = self.update_camera(cam, dets, timestamp)
        return results

    def get_tracker(self, camera_name: str) -> SimpleByteTracker | None:
        return self._trackers.get(camera_name)
