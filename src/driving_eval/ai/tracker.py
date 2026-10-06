"""ByteTrack-style Multi-Object Tracker for stable tracking of cones, lines, and obstacles.

Associates detections across consecutive frames to maintain consistent track IDs,
which is critical for debounce and duplicate violation prevention.
"""

from collections.abc import Sequence
from dataclasses import dataclass

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


@dataclass
class TrackedObject:
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


class SimpleByteTracker:
    """Lightweight deterministic tracker associating high and low confidence detections."""

    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_invisible_frames: int = 15,
        min_hits_to_confirm: int = 3,
    ):
        self.iou_threshold = iou_threshold
        self.max_invisible_frames = max_invisible_frames
        self.min_hits_to_confirm = min_hits_to_confirm
        self._next_id: int = 1
        self._tracks: dict[int, TrackedObject] = {}

    def update(self, detections: Sequence[Detection], timestamp: float) -> list[Detection]:
        """Updates tracks with new detections and injects track_id into detections."""
        updated_detections: list[Detection] = []
        matched_track_ids: set[int] = set()
        unmatched_dets: list[Detection] = []

        # Sort detections by confidence descending
        sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)

        for det in sorted_dets:
            best_iou = 0.0
            best_track_id: int | None = None

            for t_id, track in self._tracks.items():
                if t_id in matched_track_ids or track.camera != det.camera:
                    continue
                # Calculate IoU
                iou = calculate_iou(track.bbox, det.bbox)
                if iou > best_iou and iou >= self.iou_threshold:
                    best_iou = iou
                    best_track_id = t_id

            if best_track_id is not None:
                matched_track_ids.add(best_track_id)
                tr = self._tracks[best_track_id]
                tr.bbox = det.bbox
                tr.confidence = det.confidence
                tr.last_seen_timestamp = timestamp
                tr.hits += 1
                tr.age += 1
                tr.consecutive_invisible = 0

                det.track_id = best_track_id
                updated_detections.append(det)
            else:
                unmatched_dets.append(det)

        # Create new tracks for unmatched detections
        for det in unmatched_dets:
            new_id = self._next_id
            self._next_id += 1
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
            )
            self._tracks[new_id] = new_track
            det.track_id = new_id
            updated_detections.append(det)

        # Increment invisible count for tracks not matched
        dead_tracks = []
        for t_id, tr in self._tracks.items():
            if t_id not in matched_track_ids:
                tr.consecutive_invisible += 1
                if tr.consecutive_invisible > self.max_invisible_frames:
                    dead_tracks.append(t_id)

        for t_id in dead_tracks:
            del self._tracks[t_id]

        return updated_detections
