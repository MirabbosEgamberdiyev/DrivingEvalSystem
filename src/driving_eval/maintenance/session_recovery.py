"""Power-loss detection and session recovery service.

On system boot, detects unfinished sessions and safely finalizes or recovers them
without corrupting SQLite data or losing already recorded evidence.
"""

import logging
from typing import Literal

from driving_eval.db.repository import DatabaseRepository

logger = logging.getLogger("driving_eval.maintenance.recovery")


class SessionRecoveryService:
    """Handles power cut recovery and unfinished session lifecycle."""

    def __init__(self, repository: DatabaseRepository, mode: Literal["SAFE_INTERRUPT", "RESUME_ACTIVE"] = "SAFE_INTERRUPT"):
        self.repository = repository
        self.mode = mode

    def check_and_recover_on_boot(self) -> list[dict]:
        """Runs on system startup to find and resolve any incomplete sessions."""
        unfinished = self.repository.get_unfinished_sessions()
        if not unfinished:
            logger.info("Barcha o'tgan sessiyalar to'g'ri yopilgan. Tiklash talab qilinmadi.")
            return []

        logger.warning(
            "QUVVAT UZILISHI ANIQLANDI! %d ta yakunlanmagan sessiya topildi.",
            len(unfinished),
        )

        resolved_sessions = []
        for sess in unfinished:
            sess_id = sess["id"]
            if self.mode == "SAFE_INTERRUPT":
                self.repository.close_interrupted_session(
                    session_id=sess_id,
                    reason="POWER_LOSS_DETECTED_ON_BOOT",
                )
                self.repository.log_admin_action(
                    admin_user="SYSTEM_WATCHDOG",
                    action="RECOVER_POWER_LOSS",
                    target=sess_id,
                    details="Quvvat uzilishi sababli sessiya xavfsiz holda INTERRUPTED holatiga o'tkazildi",
                )
                logger.info("Sessiya %s xavfsiz tarzda INTERRUPTED deb yopildi.", sess_id)
                resolved_sessions.append(sess)
            else:
                # Mode: RESUME_ACTIVE
                logger.info("Sessiya %s qayta tiklash uchun tayyorlandi.", sess_id)
                resolved_sessions.append(sess)

        return resolved_sessions
