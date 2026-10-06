"""Offline Ed25519 licensing, hardware fingerprinting, and clock tampering protection."""

from driving_eval.licensing.clock_tamper import ClockCheckResult, ClockTamperGuard
from driving_eval.licensing.ed25519 import (
    generate_keypair,
    publickey_from_private,
    sign,
    verify,
)
from driving_eval.licensing.license_manager import (
    LicenseManager,
    LicensePayload,
    LicenseValidationResult,
    pack_license_token,
    unpack_license_token,
)
from driving_eval.licensing.machine_id import (
    MachineFingerprint,
    get_current_machine_fingerprint,
    parse_fingerprint_dict,
)

__all__ = [
    "ClockCheckResult",
    "ClockTamperGuard",
    "LicenseManager",
    "LicensePayload",
    "LicenseValidationResult",
    "MachineFingerprint",
    "generate_keypair",
    "get_current_machine_fingerprint",
    "pack_license_token",
    "parse_fingerprint_dict",
    "publickey_from_private",
    "sign",
    "unpack_license_token",
    "verify",
]
