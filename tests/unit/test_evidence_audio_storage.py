"""Unit tests for Evidence Recorder, Audio Queue & Fallback, and Storage Manager."""

import time

import numpy as np
import pytest

from driving_eval.audio.audio_service import AudioService
from driving_eval.core.config_schema import AudioConfig, StorageConfig
from driving_eval.db.repository import DatabaseRepository
from driving_eval.evidence.recorder import EvidenceRecorder
from driving_eval.evidence.storage import StorageManager
from driving_eval.hardware.camera_service import CameraFrame, FrameBundle
from driving_eval.rules.event_manager import ProcessedViolationEvent


@pytest.fixture
def repo(tmp_path):
    return DatabaseRepository(tmp_path / "test.db")


def test_evidence_recorder_creates_full_package_with_hashes(tmp_path, repo):
    evidence_dir = tmp_path / "evidence"
    recorder = EvidenceRecorder(evidence_dir, repo, buffer_duration_seconds=2.0, fps=10)

    # Push 15 frames into buffer
    for i in range(15):
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        f_bundle = FrameBundle(
            timestamp=100.0 + i * 0.1,
            frames={"FRONT": CameraFrame("FRONT", img, 100.0 + i * 0.1, i, (1280, 720))},
            is_synchronized=True,
            max_jitter_ms=5.0,
        )
        recorder.push_bundle(f_bundle)

    # Create dummy session in DB
    stu_id = repo.register_or_get_student("EV123", "Temur", "Alimov")
    veh_id = repo.register_vehicle("CAR-EV", "VINEV", "01EV", "Cobalt", 2024)
    session_id = "SESS-EV-001"
    repo.create_session(session_id, stu_id, veh_id, 100, "1.0", "1.0")

    # Record event
    event = ProcessedViolationEvent(
        violation_id="VIOL-001",
        rule_code="CONE_TOUCH",
        status="CONFIRMED",
        confidence=0.92,
        penalty=25,
        critical=False,
        camera="FRONT",
        exercise="ZMEIKA",
        details="Konus bilan to'qnashuv",
        screen_text="Konusga tegdingiz!",
        voice_file="cone_touch.wav",
        voice_text="Konusga tegdilar",
        timestamp=101.5,
        evidence_metadata={"bbox": [100, 100, 200, 200]},
    )

    ev_id = recorder.record_evidence_package(session_id, event)
    assert ev_id.startswith("EVID-")

    pkg_dir = evidence_dir / session_id / event.violation_id
    assert (pkg_dir / "before.jpg").exists()
    assert (pkg_dir / "event.jpg").exists()
    assert (pkg_dir / "after.jpg").exists()
    assert (pkg_dir / "event.mp4").exists()
    assert (pkg_dir / "metadata.json").exists()

    # Verify SHA-256 hashes exist in DB
    with repo.get_connection() as conn:
        cur = conn.execute("SELECT * FROM evidence WHERE session_id = ?", (session_id,))
        records = cur.fetchall()
        assert len(records) == 5  # 3 images + 1 video + 1 json
        for r in records:
            assert len(r["sha256_hash"]) == 64


def test_audio_service_sequential_and_fallback(tmp_path):
    cfg = AudioConfig(
        enabled=True,
        backend="wav_primary",
        audio_dir=str(tmp_path / "audio"),
        volume=1.0,
    )
    service = AudioService(cfg, simulate_playback=True)
    service.start()

    try:
        # Enqueue 2 alerts (files don't exist yet, should trigger fallback without error)
        service.enqueue_alert("test1.wav", "Birinchi xabar", critical=False)
        service.enqueue_alert("critical.wav", "Kritik xabar", critical=True)

        time.sleep(0.3)
        assert len(service.played_history) == 2
        # Critical alert should play first due to priority!
        assert service.played_history[0] == "critical.wav"
        assert service.played_history[1] == "test1.wav"
    finally:
        service.stop()


def test_storage_manager_export_and_prune(tmp_path, repo):
    base_data = tmp_path / "storage_test"
    ev_dir = base_data / "evidence"
    ev_dir.mkdir(parents=True)

    session_id = "SESS-OLD-01"
    sess_folder = ev_dir / session_id
    sess_folder.mkdir()
    (sess_folder / "test.jpg").write_text("fake evidence")

    cfg = StorageConfig(
        base_dir=str(base_data),
        db_path=str(tmp_path / "db.db"),
        evidence_dir=str(ev_dir),
        min_free_disk_gb=1.0,
        prune_threshold_gb=999999.0,  # Force low space trigger
    )

    stu_id = repo.register_or_get_student("STU-OLD", "Old", "Student")
    veh_id = repo.register_vehicle("CAR-OLD", "VINOLD", "01OLD", "Cobalt", 2024)
    repo.create_session(session_id, stu_id, veh_id, 100, "1.0", "1.0")

    mgr = StorageManager(cfg, repo)

    # 1. Test USB Export
    usb_target = tmp_path / "usb_drive"
    exported_dir = mgr.export_session_to_usb(session_id, usb_target)
    assert (exported_dir / "evidence" / "test.jpg").exists()

    # 2. Finalize session in DB so it's eligible for pruning
    repo.finalize_test_result(session_id, 100, "PASS", 0, 0)

    # 3. Test Pruning
    pruned = mgr.prune_old_evidence_if_needed()
    assert pruned == 1
    assert not sess_folder.exists()  # Evidences cleaned!
