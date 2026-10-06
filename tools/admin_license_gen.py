#!/usr/bin/env python3
"""Admin License Generator Utility for Offline Driving Evaluation System.

Generates Ed25519 cryptographically signed license tokens binding vehicle car_id,
tolerant hardware machine fingerprints, expiration dates, and tier privileges.
Kept securely by the authority / exam administrator.
"""

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from driving_eval.licensing.ed25519 import (
    generate_keypair,
    sign,
)
from driving_eval.licensing.license_manager import (
    LicensePayload,
    pack_license_token,
)
from driving_eval.licensing.machine_id import (
    MachineFingerprint,
    get_current_machine_fingerprint,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("admin_license_gen")

# Master Vendor Private Key Seed (Derived deterministically for standard vendor authority)
DEFAULT_VENDOR_PRIVATE_KEY_HEX: str = "bdd0b1a5fdd912b838c5cd6a6d08bc58caa1174c6f6a30df78cd157a1eb53869"


def create_signed_license(
    car_id: str,
    fingerprint: MachineFingerprint,
    expires_at: str = "PERMANENT",
    tier: str = "FULL",
    features: list[str] | None = None,
    private_key_hex: str = DEFAULT_VENDOR_PRIVATE_KEY_HEX,
) -> str:
    """Signs and packs an offline activation token using Ed25519 private key."""
    priv_bytes = bytes.fromhex(private_key_hex)
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = LicensePayload(
        car_id=car_id,
        machine_fingerprint=fingerprint.to_dict(),
        issued_at=now_iso,
        expires_at=expires_at,
        tier=tier,
        features=features or ["4_cameras", "all_exercises", "pdf_reports"],
    )

    payload_dict = {
        "car_id": payload.car_id,
        "machine_fingerprint": payload.machine_fingerprint,
        "issued_at": payload.issued_at,
        "expires_at": payload.expires_at,
        "tier": payload.tier,
        "features": payload.features,
    }
    json_bytes = json.dumps(payload_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = sign(json_bytes, priv_bytes)

    token = pack_license_token(payload, signature)
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="Admin Ed25519 License Generator")
    parser.add_argument("--car-id", type=str, default="CAR-UZ-01", help="Vehicle Car ID")
    parser.add_argument("--expires", type=str, default="2027-12-31", help="Expiration date (YYYY-MM-DD or PERMANENT)")
    parser.add_argument("--tier", type=str, default="FULL", choices=["FULL", "TRAINING", "ASSESSMENT"], help="License tier")
    parser.add_argument("--features", type=str, default="4_cameras,all_exercises,pdf_reports", help="Comma-separated features")
    parser.add_argument("--private-key", type=str, default=DEFAULT_VENDOR_PRIVATE_KEY_HEX, help="Ed25519 Private key in hex")
    parser.add_argument("--current-machine", action="store_true", help="Bind to current machine's actual hardware")
    parser.add_argument("--machine-json", type=Path, help="Path to machine fingerprint JSON file")
    parser.add_argument("--output", type=Path, help="Output path to save license token (e.g. config/license.key)")
    parser.add_argument("--generate-keypair", action="store_true", help="Generate a new Ed25519 root keypair")

    args = parser.parse_args()

    if args.generate_keypair:
        priv, pub = generate_keypair()
        print("\n" + "=" * 60)
        print("YANGI ED25519 ASIMMETRIK KALITLAR JUFTLIGI")
        print("=" * 60)
        print(f"Maxfiy Kalit (Private Key Hex) : {priv.hex()}")
        print(f"Ochiq Kalit (Public Key Hex)   : {pub.hex()}")
        print("=" * 60 + "\n")
        return 0

    # Determine fingerprint
    if args.current_machine or not args.machine_json:
        fp = get_current_machine_fingerprint()
        logger.info("Joriy kompyuter apparat barmoq izi ishlatilmoqda: %s", fp.canonical_id)
    else:
        with open(args.machine_json, encoding="utf-8") as f:
            data = json.load(f)
            fp = MachineFingerprint(
                board_hash=data.get("board", ""),
                cpu_hash=data.get("cpu", ""),
                disk_hash=data.get("disk", ""),
                mac_hash=data.get("mac", ""),
            )
        logger.info("JSON fayldan yuklangan apparat barmoq izi: %s", fp.canonical_id)

    features = [f.strip() for f in args.features.split(",") if f.strip()]

    # If private key was passed as a file path
    priv_hex = args.private_key
    if Path(priv_hex).exists():
        priv_hex = Path(priv_hex).read_text(encoding="utf-8").strip()

    token = create_signed_license(
        car_id=args.car_id,
        fingerprint=fp,
        expires_at=args.expires,
        tier=args.tier,
        features=features,
        private_key_hex=priv_hex,
    )

    print("\n" + "=" * 70)
    print("MUVAOFFAQIYATLI GENERATSIYA QILINGAN LITSENZIYA TOKENI:")
    print("=" * 70)
    print(token)
    print("=" * 70)
    print(f"Avtomobil ID: {args.car_id}")
    print(f"Muddat:       {args.expires}")
    print(f"Daraja:       {args.tier}")
    print(f"Machine ID:   {fp.canonical_id}")
    print("=" * 70 + "\n")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(token + "\n", encoding="utf-8")
        logger.info("Litsenziya faylga yozildi: %s", args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
