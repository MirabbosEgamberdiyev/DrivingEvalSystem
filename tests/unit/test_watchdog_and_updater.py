"""Unit tests for ProcessWatchdog and USBUpdater with rollback."""

import hashlib
import json
import time
import zipfile

from driving_eval.db.repository import DatabaseRepository
from driving_eval.maintenance.updater import USBUpdater
from driving_eval.maintenance.watchdog import ProcessWatchdog


def test_watchdog_detects_dead_process_and_calls_restart():
    restarted = []

    def on_restart(proc_name: str):
        restarted.append(proc_name)

    watchdog = ProcessWatchdog(
        heartbeat_timeout_seconds=0.2,
        check_interval_seconds=0.05,
        restart_callback=on_restart,
    )
    watchdog.register_process("ai_inference_worker")
    watchdog.start()

    try:
        # Give it a heartbeat
        watchdog.record_heartbeat("ai_inference_worker")
        time.sleep(0.1)
        assert len(restarted) == 0

        # Now simulate process freeze (> 0.2s without heartbeat)
        time.sleep(0.25)
        assert "ai_inference_worker" in restarted
    finally:
        watchdog.stop()


def test_usb_updater_backup_update_and_rollback(tmp_path):
    app_root = tmp_path / "app"
    backup_dir = tmp_path / "backups"
    usb_dir = tmp_path / "usb"

    app_root.mkdir()
    (app_root / "src").mkdir()
    (app_root / "config").mkdir()
    (app_root / "src" / "version.txt").write_text("v1.0.0")

    repo = DatabaseRepository(tmp_path / "updater_test.db")
    updater = USBUpdater(app_root, backup_dir, repo)

    # 1. Create a dummy update package on USB
    usb_dir.mkdir()
    update_content_dir = tmp_path / "update_content"
    update_content_dir.mkdir()
    (update_content_dir / "src").mkdir()
    (update_content_dir / "src" / "version.txt").write_text("v2.0.0")

    zip_file = usb_dir / "update_package.zip"
    with zipfile.ZipFile(zip_file, "w") as z:
        z.write(update_content_dir / "src" / "version.txt", arcname="src/version.txt")

    # Compute SHA-256 for manifest
    hasher = hashlib.sha256()
    with open(zip_file, "rb") as f:
        hasher.update(f.read())
    pkg_hash = hasher.hexdigest()

    manifest = {"version": "2.0.0", "package_sha256": pkg_hash}
    with open(usb_dir / "update_manifest.json", "w") as f:
        json.dump(manifest, f)

    # 2. Apply update
    success = updater.apply_update_from_usb(usb_dir)
    assert success is True
    assert (app_root / "src" / "version.txt").read_text() == "v2.0.0"

    # 3. Test Rollback
    rollback_ok = updater.rollback()
    assert rollback_ok is True
    assert (app_root / "src" / "version.txt").read_text() == "v1.0.0"


def test_watchdog_service_heartbeats_and_metrics():
    from driving_eval.watchdog.watchdog_service import WatchdogService

    restarts: list[str] = []
    watchdog = WatchdogService(
        heartbeat_timeout_seconds=0.15,
        check_interval_seconds=0.04,
        restart_callback=lambda name: restarts.append(name),
    )
    watchdog.register_worker("camera_worker")
    watchdog.register_worker("ai_worker")
    watchdog.start()

    try:
        # Both alive
        assert watchdog.is_alive("camera_worker") is True
        assert watchdog.is_alive("ai_worker") is True

        # Keep camera_worker alive, let ai_worker time out
        for _ in range(5):
            watchdog.record_heartbeat("camera_worker")
            time.sleep(0.04)

        time.sleep(0.12)
        # ai_worker should have triggered restart
        assert "ai_worker" in restarts
        metrics = watchdog.get_metrics()
        assert metrics["running"] is True
        assert metrics["monitored_count"] == 2
        assert "camera_worker" in metrics["workers"]
    finally:
        watchdog.stop()


def test_watchdog_service_restart_rate_limiting():
    from driving_eval.watchdog.watchdog_service import WatchdogService

    watchdog = WatchdogService(
        max_restarts_per_window=2,
        restart_window_seconds=10.0,
    )
    # First 2 allowed
    assert watchdog._should_allow_restart("failing_worker") is True
    assert watchdog._should_allow_restart("failing_worker") is True
    # 3rd should be blocked by rate limiter
    assert watchdog._should_allow_restart("failing_worker") is False


def test_crash_bundle_exporter_creates_valid_bundle_and_hashes(tmp_path):
    import sqlite3

    from driving_eval.watchdog.watchdog_service import CrashBundleExporter

    out_dir = tmp_path / "bundles"
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "system.log").write_text("2026-10-06 INFO System started\n", encoding="utf-8")

    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE test_data (id INTEGER PRIMARY KEY, msg TEXT);")
        conn.execute("INSERT INTO test_data (msg) VALUES ('diagnostics test');")
        conn.commit()

    bundle_path = CrashBundleExporter.create_diagnostics_bundle(
        output_dir=out_dir,
        db_path=db_path,
        log_dir=log_dir,
        app_state_info={"state": "TEST_ACTIVE", "session_id": "sess_123"},
    )

    assert bundle_path.exists()
    assert bundle_path.name.endswith(".zip")
    sha_file = out_dir / f"{bundle_path.name}.sha256"
    assert sha_file.exists()

    # Verify zip content
    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = zf.namelist()
        assert "system_info.json" in names
        assert "app_state.json" in names
        assert "logs/system.log" in names
        assert "database/evaluation_snapshot.db" in names
        assert "bundle_manifest.json" in names

        # Validate system_info JSON
        telemetry = json.loads(zf.read("system_info.json").decode("utf-8"))
        assert "os_system" in telemetry
        assert "cpu_logical_cores" in telemetry
        assert "python_version" in telemetry


def test_inno_setup_scripts_and_multilingual_isl_validity():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    iss_file = repo_root / "installer" / "setup.iss"
    assert iss_file.exists(), "installer/setup.iss must exist"
    iss_text = iss_file.read_text(encoding="utf-8")
    assert "MyAppName" in iss_text
    assert "uz_Latn" in iss_text
    assert "uz_Cyrl" in iss_text
    assert "ru" in iss_text

    # Verify ISL files for all 3 languages
    for lang, fname in [
        ("uz-Latn", "uz-Latn.isl"),
        ("uz-Cyrl", "uz-Cyrl.isl"),
        ("ru", "Russian.isl"),
    ]:
        isl_path = repo_root / "installer" / "languages" / fname
        assert isl_path.exists(), f"ISL file {fname} must exist"
        isl_content = isl_path.read_text(encoding="utf-8")
        assert "[CustomMessages]" in isl_content
        assert "AppTitle" in isl_content
        assert "CreateDesktopIcon" in isl_content
        assert "KioskModeShortcut" in isl_content


def test_build_standalone_tree_assembly(tmp_path):
    from pathlib import Path

    from scripts.build_standalone import assemble_distribution_tree

    repo_root = Path(__file__).resolve().parent.parent.parent
    target_dist = tmp_path / "dist"

    assemble_distribution_tree(target_dist, repo_root)

    # Verify copied structures
    assert (target_dist / "config" / "rules.yaml").exists()
    assert (target_dist / "data" / "audio" / "uz-Latn").exists()
    assert (target_dist / "driving_eval" / "i18n" / "catalogs" / "uz-Latn.json").exists()
    assert (target_dist / "driving_eval" / "ui_qml" / "qml" / "Main.qml").exists()

