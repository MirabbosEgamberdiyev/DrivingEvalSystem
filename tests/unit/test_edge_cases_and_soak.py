"""Edge cases and reliability tests: disk thresholds, SQLite WAL concurrency, camera disconnects, clock rollback."""

import concurrent.futures
import json
import shutil
import sqlite3
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from driving_eval.core.config_schema import CameraDeviceConfig, CamerasConfig, StorageConfig
from driving_eval.db.repository import DatabaseRepository
from driving_eval.evidence.storage import StorageManager
from driving_eval.hardware.camera_service import MultiCameraService, StreamStatus
from driving_eval.licensing.clock_tamper import ClockTamperGuard


def test_disk_low_and_critical_threshold_handling(tmp_path: Path) -> None:
    """Verifies that disk usage monitoring detects low space (<10GB), triggers pruning, and flags critical (<2GB)."""
    db_file = tmp_path / "test_storage.db"
    repo = DatabaseRepository(db_file)

    storage_cfg = StorageConfig(
        base_dir=str(tmp_path),
        evidence_dir=str(tmp_path / "evidence"),
        prune_threshold_gb=10.0,
    )
    mgr = StorageManager(storage_cfg, repo)

    # Register sample completed session
    stu_id = repo.register_or_get_student("STU-DISK", "Disk", "Tester")
    veh_id = repo.register_vehicle("CAR-DISK", "VINDISK", "01DISK", "Cobalt", 2024)
    sess_id = "SESS-OLD-COMPLETED"
    repo.create_session(sess_id, stu_id, veh_id, 100, "1.0", "1.0")
    repo.finalize_test_result(sess_id, final_score=90, result="PASS", critical_count=0, suspect_count=0, status="COMPLETED")

    # Create dummy evidence folder
    sess_folder = Path(storage_cfg.evidence_dir) / sess_id
    sess_folder.mkdir(parents=True, exist_ok=True)
    (sess_folder / "test.jpg").write_bytes(b"dummy image data")

    # 1. Normal state: 50 GB free
    with patch("shutil.disk_usage", return_value=shutil._ntuple_diskusage(100 * 1024**3, 50 * 1024**3, 50 * 1024**3)):
        res = mgr.check_disk_space(critical_threshold_gb=2.0)
        assert res["free_space_gb"] == 50.0
        assert res["is_low"] is False
        assert res["is_critical"] is False
        assert res["pruned_sessions"] == 0
        assert sess_folder.exists()

    # 2. Low space: 8 GB free (< 10 GB prune threshold)
    with patch("shutil.disk_usage", return_value=shutil._ntuple_diskusage(100 * 1024**3, 92 * 1024**3, 8 * 1024**3)):
        res_low = mgr.check_disk_space(critical_threshold_gb=2.0)
        assert res_low["is_low"] is True
        assert res_low["pruned_sessions"] == 1
        assert not sess_folder.exists(), "Completed session evidence should be pruned"

    # 3. Critical space: 1.2 GB free (< 2.0 GB critical threshold)
    with patch("shutil.disk_usage", return_value=shutil._ntuple_diskusage(100 * 1024**3, 98.8 * 1024**3, 1.2 * 1024**3)):
        assert mgr.is_critically_low(critical_threshold_gb=2.0) is True
        res_crit = mgr.check_disk_space(critical_threshold_gb=2.0)
        assert res_crit["is_critical"] is True


def test_sqlite_wal_rapid_concurrent_transactions(tmp_path: Path) -> None:
    """Stress tests SQLite WAL concurrency with rapid multi-threaded writes, ensuring 0 locks and valid hash chain."""
    db_file = tmp_path / "concurrent_stress.db"
    repo = DatabaseRepository(db_file)
    repo.sync_rules("config/rules.yaml")

    num_threads = 6
    iterations_per_thread = 15

    def worker_task(thread_idx: int) -> list[str]:
        session_ids = []
        for i in range(iterations_per_thread):
            stu_id = repo.register_or_get_student(f"STU-TH{thread_idx}-{i}", "Stress", f"Thread{thread_idx}")
            veh_id = repo.register_vehicle(f"CAR-TH{thread_idx}-{i}", f"VIN{thread_idx}{i}", f"01TH{thread_idx}", "Cobalt", 2024)
            sess_id = f"SESS-TH{thread_idx}-{i}"
            session_ids.append(sess_id)

            repo.create_session(sess_id, stu_id, veh_id, 100, "1.0", "1.0")

            # Write violation
            v_id = f"VIO-TH{thread_idx}-{i}"
            desc = json.dumps({"offset": 12, "thread": thread_idx})
            repo.record_violation(v_id, sess_id, "CONFIRMED", 0.95, "FRONT", "ESTAKADA", "STOP_LINE_VIOLATION", desc)
            repo.finalize_test_result(sess_id, final_score=95, result="PASS", critical_count=0, suspect_count=0, status="COMPLETED")
        return session_ids

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_task, idx) for idx in range(num_threads)]
        all_sessions = []
        for fut in concurrent.futures.as_completed(futures):
            all_sessions.extend(fut.result())

    assert len(all_sessions) == num_threads * iterations_per_thread

    # Verify that all sessions exist and their hash chain integrity is 100% verified
    for sess_id in all_sessions:
        sess = repo.get_session(sess_id)
        assert sess is not None
        assert sess["status"] == "COMPLETED"
        assert repo.verify_session_hash_integrity(sess_id) is True


def test_camera_disconnect_detection() -> None:
    """Verifies that MultiCameraService detects camera drops or frame acquisition timeouts."""
    cam_cfg = CamerasConfig(
        sync_tolerance_ms=45,
        devices={
            "FRONT": CameraDeviceConfig(name="FRONT", device_index=0, width=640, height=480, fps=30),
            "REAR": CameraDeviceConfig(name="REAR", device_index=1, width=640, height=480, fps=30),
        },
    )
    service = MultiCameraService(cam_cfg, simulation_mode=True)

    # Mock both cameras as online and delivering frames actively
    now = time.monotonic()
    for cam_name in ("FRONT", "REAR"):
        mock_worker = MagicMock()
        mock_h = MagicMock()
        mock_h.status = StreamStatus.ONLINE
        mock_h.total_frames = 100
        mock_h.last_frame_timestamp = now
        mock_worker.get_health.return_value = mock_h
        service.workers[cam_name] = mock_worker

    # Both online: no disconnected cameras
    assert service.get_disconnected_cameras(timeout_sec=1.0) == []

    # 1. Simulate REAR going OFFLINE (USB cable pulled)
    mock_rear_health = MagicMock()
    mock_rear_health.status = StreamStatus.OFFLINE
    mock_rear_health.total_frames = 100
    mock_rear_health.last_frame_timestamp = now
    service.workers["REAR"].get_health.return_value = mock_rear_health

    disconnected = service.get_disconnected_cameras(timeout_sec=1.0)
    assert "REAR" in disconnected
    assert "FRONT" not in disconnected

    # 2. Simulate FRONT freezing (stale frames for 4 seconds)
    mock_rear_health.status = StreamStatus.ONLINE
    mock_front_health = MagicMock()
    mock_front_health.status = StreamStatus.ONLINE
    mock_front_health.total_frames = 100
    mock_front_health.last_frame_timestamp = now - 4.0
    service.workers["FRONT"].get_health.return_value = mock_front_health

    stale_disconnected = service.get_disconnected_cameras(timeout_sec=2.0)
    assert "FRONT" in stale_disconnected
    assert "REAR" not in stale_disconnected


def test_clock_rollback_and_hash_tamper_detection(tmp_path: Path) -> None:
    """Verifies clock rollback detection and tamper detection in clock guard."""
    db_path = tmp_path / "test_clock.db"
    guard = ClockTamperGuard(db_path=str(db_path), grace_seconds=15.0)

    t0 = 1700000000.0
    guard.record_timestamp_anchor(current_time=t0)
    guard.record_timestamp_anchor(current_time=t0 + 50.0)

    # Valid forward check
    assert guard.check_clock_validity(current_time=t0 + 60.0).valid is True

    # Rollback 1 hour
    rollback_res = guard.check_clock_validity(current_time=t0 - 3600.0)
    assert rollback_res.valid is False
    assert rollback_res.error == "CLOCK_ROLLBACK_DETECTED"

    # SQLite direct tamper
    conn = sqlite3.connect(str(db_path))
    conn.execute("UPDATE clock_timeline SET timestamp = 1700000010.0 WHERE id = 1")
    conn.commit()
    conn.close()

    tamper_res = guard.check_clock_validity(current_time=t0 + 100.0)
    assert tamper_res.valid is False
