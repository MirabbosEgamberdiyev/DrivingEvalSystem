"""USB Offline Updater with SHA-256 verification, automatic backup, and rollback."""

import hashlib
import json
import logging
import shutil
import zipfile
from pathlib import Path

from driving_eval.db.repository import DatabaseRepository

logger = logging.getLogger("driving_eval.maintenance.updater")


class USBUpdater:
    """Manages offline application updates from USB drive with full rollback protection."""

    def __init__(
        self,
        app_root: str | Path,
        backup_dir: str | Path,
        repository: DatabaseRepository | None = None,
    ):
        self.app_root = Path(app_root)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.repository = repository
        self._latest_backup_path: Path | None = None

    def create_backup(self) -> Path:
        """Creates a timestamped snapshot of current application files."""
        ts = int(hashlib.md5(str(self.app_root).encode()).hexdigest()[:6], 16)
        backup_path = self.backup_dir / f"backup_v_{ts}"
        if backup_path.exists():
            shutil.rmtree(backup_path)

        # Copy essential folders (src, config)
        backup_path.mkdir(parents=True)
        for folder in ["src", "config"]:
            src_f = self.app_root / folder
            if src_f.exists():
                shutil.copytree(src_f, backup_path / folder)

        self._latest_backup_path = backup_path
        logger.info("Zaxira nusxasi (Backup) yaratildi: %s", backup_path)
        return backup_path

    def rollback(self) -> bool:
        """Rolls back to the latest backup in case of update failure."""
        if not self._latest_backup_path or not self._latest_backup_path.exists():
            logger.error("Rollback uchun zaxira nusxasi topilmadi!")
            return False

        logger.warning("ROLLBACK boshlandi: %s dan tiklanmoqda", self._latest_backup_path)
        for folder in ["src", "config"]:
            dest_f = self.app_root / folder
            src_f = self._latest_backup_path / folder
            if src_f.exists():
                if dest_f.exists():
                    shutil.rmtree(dest_f)
                shutil.copytree(src_f, dest_f)

        if self.repository:
            self.repository.log_admin_action(
                admin_user="UPDATER",
                action="ROLLBACK",
                target=str(self.app_root),
                details=f"Yangilanish bekor qilindi, {self._latest_backup_path} dan qaytarildi",
            )
        logger.info("Rollback muvaffaqiyatli yakunlandi.")
        return True

    def apply_update_from_usb(self, usb_mount_path: str | Path) -> bool:
        """Finds update package on USB, verifies SHA-256, backs up, and applies update."""
        usb = Path(usb_mount_path)
        pkg_file = usb / "update_package.zip"
        manifest_file = usb / "update_manifest.json"

        if not pkg_file.exists() or not manifest_file.exists():
            logger.error("USB da yangilanish paketi topilmadi: %s", usb)
            return False

        # 1. Verify Hash
        with open(manifest_file, encoding="utf-8") as f:
            manifest = json.load(f)

        expected_hash = manifest.get("package_sha256", "")
        hasher = hashlib.sha256()
        with open(pkg_file, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        calc_hash = hasher.hexdigest()

        if calc_hash.lower() != expected_hash.lower():
            logger.error("Yangilanish fayli xeshi mos kelmadi! Kutilgan: %s, Hisoblangan: %s", expected_hash, calc_hash)
            return False

        # 2. Backup current state
        self.create_backup()

        # 3. Extract and Apply
        try:
            with zipfile.ZipFile(pkg_file, "r") as z:
                z.extractall(self.app_root)
            logger.info("Yangilanish paketi muvaffaqiyatli o'rnatildi: v%s", manifest.get("version", "unknown"))

            if self.repository:
                self.repository.log_admin_action(
                    admin_user="UPDATER",
                    action="APPLY_UPDATE",
                    target=manifest.get("version", ""),
                    details=f"Yangi versiya o'rnatildi: {pkg_file}",
                )
            return True
        except Exception as e:
            logger.error("Yangilashni o'rnatishda xato: %s. Rollback boshlanadi.", e)
            self.rollback()
            return False
