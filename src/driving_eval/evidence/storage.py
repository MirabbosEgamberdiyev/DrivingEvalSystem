"""Storage Manager for SSD disk usage monitoring, safe evidence pruning, and USB export."""

import json
import logging
import shutil
import time
from pathlib import Path

from driving_eval.core.config_schema import StorageConfig
from driving_eval.db.repository import DatabaseRepository

logger = logging.getLogger("driving_eval.evidence.storage")


class StorageManager:
    """Monitors disk space, handles safe pruning, and manages USB bundle export with cryptographic manifests."""

    def __init__(self, config: StorageConfig, repository: DatabaseRepository):
        self.config = config
        self.repository = repository
        self.base_dir = Path(config.base_dir)
        self.evidence_dir = Path(config.evidence_dir)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def get_free_space_gb(self) -> float:
        """Returns free disk space in GB on evidence partition."""
        usage = shutil.disk_usage(self.base_dir)
        return usage.free / (1024**3)

    def is_space_low(self) -> bool:
        """Returns True if free space is below the critical threshold."""
        return self.get_free_space_gb() < self.config.prune_threshold_gb

    def export_session_to_usb(self, session_id: str, usb_target_path: str | Path) -> Path:
        """Exports full session evidence, metadata, and signed manifest to USB drive."""
        usb_dest = Path(usb_target_path) / f"EXAM_EXPORT_{session_id}"
        usb_dest.mkdir(parents=True, exist_ok=True)

        session_evidence_dir = self.evidence_dir / session_id
        exported_files: list[dict[str, str]] = []

        if session_evidence_dir.exists():
            evidence_dest = usb_dest / "evidence"
            shutil.copytree(session_evidence_dir, evidence_dest, dirs_exist_ok=True)

            # Compute manifest hashes for all exported files
            for p in evidence_dest.rglob("*"):
                if p.is_file():
                    h = self.repository.compute_file_sha256(p)
                    rel_p = str(p.relative_to(usb_dest)).replace("\\", "/")
                    exported_files.append({"path": rel_p, "sha256": h})

        session_info = self.repository.get_session(session_id) or {}

        # Write export_manifest.json
        manifest = {
            "session_id": session_id,
            "exported_at": time.time(),
            "exported_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "session_info": session_info,
            "files_count": len(exported_files),
            "files": exported_files,
        }
        manifest_path = usb_dest / "export_manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # Log admin audit
        self.repository.log_admin_action(
            admin_user="INSPECTOR",
            action="EXPORT_USB",
            target=session_id,
            details=f"Sessiya dalillari va manifesti USB ga nusxalandi: {usb_dest} ({len(exported_files)} ta fayl)",
        )
        logger.info("Sessiya %s USB ga eksport qilindi: %s", session_id, usb_dest)
        return usb_dest

    def prune_old_evidence_if_needed(self) -> int:
        """Prunes evidence directories of completed sessions if disk space is critical.

        Never deletes active session files or SQLite database records.
        Returns count of pruned sessions.
        """
        if not self.is_space_low():
            return 0

        logger.warning(
            "Diskda joy oz qoldi (%.2f GB < %.2f GB)! Eski dalillarni tozalash boshlandi.",
            self.get_free_space_gb(),
            self.config.prune_threshold_gb,
        )

        pruned_count = 0
        for session_folder in self.evidence_dir.iterdir():
            if not session_folder.is_dir():
                continue

            session_id = session_folder.name
            session_info = self.repository.get_session(session_id)

            # Only prune if session is finalized and not currently in progress
            if session_info and session_info["status"] in ("COMPLETED", "TERMINATED", "INTERRUPTED"):
                shutil.rmtree(session_folder, ignore_errors=True)
                pruned_count += 1
                logger.info("Eski dalillar tozalandi: %s", session_id)

                if not self.is_space_low():
                    break

        return pruned_count
