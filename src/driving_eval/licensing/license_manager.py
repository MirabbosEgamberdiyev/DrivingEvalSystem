"""Offline license management and Ed25519 cryptographic activation engine.

Enforces offline machine binding (3-of-4 hardware quorum), vehicle car_id binding,
anti-clock-tampering protection, and cryptographic Ed25519 digital signature verification.
Zero network access required.
"""

import base64
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from driving_eval.licensing.clock_tamper import ClockTamperGuard
from driving_eval.licensing.ed25519 import verify
from driving_eval.licensing.machine_id import (
    MachineFingerprint,
    get_current_machine_fingerprint,
    parse_fingerprint_dict,
)

logger = logging.getLogger("driving_eval.licensing")

# Embedded Master Ed25519 Public Key for offline verification
MASTER_PUBLIC_KEY_HEX: str = "1ddb2af429f68934270ffb85dd1fbe5d0be16af795fb6dc24f9ce67c931d2aa3"


@dataclass
class LicensePayload:
    car_id: str
    machine_fingerprint: dict[str, str]
    issued_at: str
    expires_at: str  # ISO 8601 or 'PERMANENT'
    tier: str = "FULL"  # 'FULL', 'TRAINING', 'ASSESSMENT'
    features: list[str] = field(default_factory=lambda: ["4_cameras", "all_exercises", "pdf_reports"])


@dataclass
class LicenseValidationResult:
    is_valid: bool
    status_code: str  # 'ACTIVE', 'EXPIRED', 'MACHINE_MISMATCH', 'CAR_ID_MISMATCH', 'INVALID_SIGNATURE', 'CLOCK_ROLLBACK', 'MALFORMED'
    error_message: str | None = None
    car_id: str | None = None
    tier: str | None = None
    expires_at: str | None = None
    matching_components: int = 0
    features: list[str] = field(default_factory=list)


def pack_license_token(payload: LicensePayload, signature_bytes: bytes) -> str:
    """Serializes a license payload and 64-byte Ed25519 signature into a formatted token string."""
    payload_dict = {
        "car_id": payload.car_id,
        "machine_fingerprint": payload.machine_fingerprint,
        "issued_at": payload.issued_at,
        "expires_at": payload.expires_at,
        "tier": payload.tier,
        "features": payload.features,
    }
    json_bytes = json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    blob = len(json_bytes).to_bytes(4, "big") + json_bytes + signature_bytes
    b64 = base64.urlsafe_b64encode(blob).decode("ascii").rstrip("=")
    return f"DRV-LIC-{b64}"


def unpack_license_token(token_str: str) -> tuple[dict[str, Any], bytes]:
    """Deserializes token string into payload dictionary and signature bytes."""
    cleaned = token_str.strip()
    if cleaned.startswith("DRV-LIC-"):
        cleaned = cleaned[8:]

    # Add base64 padding
    missing_padding = len(cleaned) % 4
    if missing_padding:
        cleaned += "=" * (4 - missing_padding)

    blob = base64.urlsafe_b64decode(cleaned.encode("ascii"))
    if len(blob) < 4 + 64:
        raise ValueError("Litsenziya tokeni formati noto'g'ri (juda qisqa).")

    json_len = int.from_bytes(blob[:4], "big")
    if len(blob) < 4 + json_len + 64:
        raise ValueError("Litsenziya tokeni ma'lumotlari to'liq emas.")

    json_bytes = blob[4 : 4 + json_len]
    signature_bytes = blob[4 + json_len : 4 + json_len + 64]
    payload_dict = json.loads(json_bytes.decode("utf-8"))

    return payload_dict, signature_bytes


class LicenseManager:
    """Handles offline validation and file storage of system licenses."""

    def __init__(
        self,
        public_key_hex: str = MASTER_PUBLIC_KEY_HEX,
        license_file_path: str | Path = "config/license.key",
        db_path: str = "data/db/driving_eval.db",
        clock_guard: ClockTamperGuard | None = None,
    ):
        self.public_key_bytes = bytes.fromhex(public_key_hex)
        self.license_file_path = Path(license_file_path)
        self.db_path = str(db_path)
        self.clock_guard = clock_guard or ClockTamperGuard(db_path=self.db_path)

    def validate(
        self,
        token_str: str,
        expected_car_id: str | None = None,
        current_fingerprint: MachineFingerprint | None = None,
        test_now_timestamp: float | None = None,
    ) -> LicenseValidationResult:
        """Validates license signature, machine quorum, clock tampering, and expiration."""
        # 1. Unpack token
        try:
            payload_dict, signature_bytes = unpack_license_token(token_str)
        except Exception as ex:
            return LicenseValidationResult(
                is_valid=False,
                status_code="MALFORMED",
                error_message=f"Litsenziya tokenini o'qib bo'lmadi: {ex}",
            )

        # 2. Cryptographic signature check
        reconstructed_json_bytes = json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
        is_signature_valid = verify(signature_bytes, reconstructed_json_bytes, self.public_key_bytes)
        if not is_signature_valid:
            logger.error("Litsenziya Ed25519 raqamli imzosi haqiqiy emas!")
            return LicenseValidationResult(
                is_valid=False,
                status_code="INVALID_SIGNATURE",
                error_message="Litsenziya raqamli imzosi noto'g'ri yoki fayl o'zgartirilgan.",
            )

        car_id = payload_dict.get("car_id", "")
        tier = payload_dict.get("tier", "FULL")
        expires_at = payload_dict.get("expires_at", "")
        features = payload_dict.get("features", [])

        # 3. Check car_id binding
        if expected_car_id and car_id != expected_car_id:
            logger.warning("Litsenziya car_id (%s) konfiguratsiyaga (%s) mos kelmadi.", car_id, expected_car_id)
            return LicenseValidationResult(
                is_valid=False,
                status_code="CAR_ID_MISMATCH",
                error_message=f"Ushbu litsenziya boshqa avtomobilga ({car_id}) tegishli.",
                car_id=car_id,
                tier=tier,
                expires_at=expires_at,
            )

        # 4. Check hardware quorum (3 out of 4 components must match)
        target_fp = parse_fingerprint_dict(payload_dict.get("machine_fingerprint", {}))
        actual_fp = current_fingerprint or get_current_machine_fingerprint()
        is_hw_match, match_count = actual_fp.match(target_fp, min_matching=3)
        if not is_hw_match:
            logger.error(
                "Apparat kvorumi bajarilmadi! Mos kelgan komponentlar: %d/4 (kamida 3 talab qilinadi).", match_count
            )
            return LicenseValidationResult(
                is_valid=False,
                status_code="MACHINE_MISMATCH",
                error_message=f"Litsenziya boshqa kompyuterga bog'langan ({match_count}/4 moslik).",
                car_id=car_id,
                tier=tier,
                expires_at=expires_at,
                matching_components=match_count,
            )

        # 5. Anti-Clock-Tampering validation
        clock_res = self.clock_guard.check_clock_validity(current_time=test_now_timestamp)
        if not clock_res.valid:
            logger.critical("Tizim soati manipulyatsiyasi aniqlandi: %s", clock_res.error)
            return LicenseValidationResult(
                is_valid=False,
                status_code="CLOCK_ROLLBACK",
                error_message="Tizim soati orqaga surilganligi sababli litsenziya bloklandi.",
                car_id=car_id,
                tier=tier,
                expires_at=expires_at,
            )

        # 6. Check expiration
        now_ts = test_now_timestamp if test_now_timestamp is not None else time.time()
        if expires_at and expires_at.upper() != "PERMANENT":
            try:
                # Support ISO formats: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ
                if "T" in expires_at:
                    dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                else:
                    dt = datetime.strptime(expires_at, "%Y-%m-%d").replace(tzinfo=UTC)
                expiry_ts = dt.timestamp()
                if now_ts > expiry_ts:
                    logger.warning("Litsenziya muddati tugagan: %s (Hozir: %s)", expires_at, now_ts)
                    return LicenseValidationResult(
                        is_valid=False,
                        status_code="EXPIRED",
                        error_message=f"Litsenziya muddati tugagan: {expires_at}",
                        car_id=car_id,
                        tier=tier,
                        expires_at=expires_at,
                        matching_components=match_count,
                    )
            except Exception as ex:
                logger.warning("Amal qilish muddatini tekshirishda xato: %s", ex)

        # Record verified timestamp anchor
        try:
            self.clock_guard.record_timestamp_anchor(current_time=now_ts)
        except Exception as ex:
            logger.warning("Soat muhrini qayd qilishda ogohlantirish: %s", ex)

        return LicenseValidationResult(
            is_valid=True,
            status_code="ACTIVE",
            car_id=car_id,
            tier=tier,
            expires_at=expires_at,
            matching_components=match_count,
            features=features,
        )

    def load_license_file(self) -> str | None:
        """Loads raw license token from disk."""
        if not self.license_file_path.exists():
            return None
        try:
            return self.license_file_path.read_text(encoding="utf-8").strip()
        except Exception as ex:
            logger.warning("Litsenziya faylini o'qishda xato: %s", ex)
            return None

    def save_license_file(self, token_str: str) -> None:
        """Saves verified license token to disk."""
        self.license_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.license_file_path.write_text(token_str.strip(), encoding="utf-8")
        logger.info("Litsenziya saqlandi: %s", self.license_file_path)

    def verify_stored_license(self, expected_car_id: str | None = None) -> LicenseValidationResult:
        """Checks stored license file."""
        token = self.load_license_file()
        if not token:
            return LicenseValidationResult(
                is_valid=False,
                status_code="NOT_FOUND",
                error_message="Litsenziya fayli topilmadi.",
            )
        return self.validate(token, expected_car_id=expected_car_id)
