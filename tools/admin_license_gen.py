#!/usr/bin/env python3
"""Admin License Generator Utility for Offline Driving Evaluation System.

Generates Ed25519 cryptographically signed license tokens binding vehicle car_id,
tolerant hardware machine fingerprints, expiration dates, and tier privileges.
Kept securely by the authority / exam administrator outside of public repositories.
"""

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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


def create_signed_license(
    car_id: str,
    fingerprint: MachineFingerprint,
    expires_at: str = "PERMANENT",
    tier: str = "FULL",
    features: list[str] | None = None,
    private_key_hex: str | None = None,
) -> str:
    """Signs and packs an offline activation token using Ed25519 private key."""
    if not private_key_hex:
        private_key_hex = os.environ.get("DRIVING_EVAL_VENDOR_KEY")

    if not private_key_hex:
        raise ValueError(
            "XATOLIK: Ed25519 xususiy kaliti ko'rsatilmadi! "
            "Iltimos, --private-key parametrini bering yoki DRIVING_EVAL_VENDOR_KEY "
            "muhit o'zgaruvchisini o'rnating."
        )

    priv_bytes = bytes.fromhex(private_key_hex)
    priv_obj = Ed25519PrivateKey.from_private_bytes(priv_bytes)
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
    signature = priv_obj.sign(json_bytes)

    token = pack_license_token(payload, signature)
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="Admin Ed25519 License Generator (Secure Offline Edition)")
    parser.add_argument("--car-id", type=str, default="CAR-UZ-01", help="Vehicle Car ID")
    parser.add_argument("--expires", type=str, default="2027-12-31", help="Expiration date (YYYY-MM-DD or PERMANENT)")
    parser.add_argument("--tier", type=str, default="FULL", choices=["FULL", "TRAINING", "ASSESSMENT"], help="License tier")
    parser.add_argument("--features", type=str, default="4_cameras,all_exercises,pdf_reports", help="Comma-separated features")
    parser.add_argument("--private-key", type=str, default=None, help="Ed25519 Private key hex or path to private key file")
    parser.add_argument("--passphrase", type=str, default=None, help="Passphrase for encrypted PEM private key")
    parser.add_argument("--current-machine", action="store_true", help="Bind to current machine's actual hardware")
    parser.add_argument("--machine-json", type=Path, help="Path to machine fingerprint JSON file")
    parser.add_argument("--output", type=Path, help="Output path to save license token (e.g. config/license.key)")
    parser.add_argument("--generate-keypair", action="store_true", help="Generate a new Ed25519 root keypair")
    parser.add_argument("--save-encrypted", type=Path, help="File path to save passphrase-encrypted private key PEM")

    args = parser.parse_args()

    if args.generate_keypair:
        priv_key = Ed25519PrivateKey.generate()
        raw_priv = priv_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_key = priv_key.public_key()
        raw_pub = pub_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        print("\n" + "=" * 70)
        print("YANGI ED25519 ASIMMETRIK KALITLAR JUFTLIGI YARATILDI")
        print("=" * 70)
        print(f"Ochiq Kalit (Public Key Hex - Dasturga kiritiladi): {raw_pub.hex()}")
        print(f"Maxfiy Kalit (Private Key Hex - MAXFIY TUTING!):   {raw_priv.hex()}")
        print("=" * 70)

        if args.save_encrypted and args.passphrase:
            encrypted_pem = priv_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(args.passphrase.encode("utf-8")),
            )
            args.save_encrypted.parent.mkdir(parents=True, exist_ok=True)
            args.save_encrypted.write_bytes(encrypted_pem)
            print(f"[+] Maxfiy kalit parol bilan shifrlanib saqlandi: {args.save_encrypted}")

        print("DIQQAT: Maxfiy kalitni hech qachon Git repozitoriyasiga yuklamang!\n")
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

    # Resolve private key
    priv_hex = args.private_key or os.environ.get("DRIVING_EVAL_VENDOR_KEY")
    if priv_hex and Path(priv_hex).exists():
        key_path = Path(priv_hex)
        key_bytes = key_path.read_bytes()
        if b"BEGIN ENCRYPTED PRIVATE KEY" in key_bytes or b"BEGIN PRIVATE KEY" in key_bytes:
            password = args.passphrase.encode("utf-8") if args.passphrase else None
            loaded_priv = serialization.load_pem_private_key(key_bytes, password=password)
            if not isinstance(loaded_priv, Ed25519PrivateKey):
                raise ValueError("Fayldagi kalit Ed25519 turi bo'lishi shart.")
            priv_hex = loaded_priv.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            ).hex()
        else:
            priv_hex = key_bytes.decode("utf-8").strip()

    if not priv_hex:
        logger.error(
            "XATOLIK: Maxfiy kalit ko'rsatilmadi! "
            "Iltimos, --private-key yoki DRIVING_EVAL_VENDOR_KEY muhit o'zgaruvchisidan foydalaning."
        )
        return 1

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
