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
