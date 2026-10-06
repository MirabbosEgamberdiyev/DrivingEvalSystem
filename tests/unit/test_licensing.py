"""Unit and integration tests for Ed25519 offline licensing and anti-tamper security."""

import sqlite3
import tempfile
from pathlib import Path

from driving_eval.licensing.clock_tamper import ClockTamperGuard
from driving_eval.licensing.ed25519 import (
    generate_keypair,
    publickey_from_private,
    sign,
    verify,
)
from driving_eval.licensing.license_manager import (
    MASTER_PUBLIC_KEY_HEX,
    LicenseManager,
    LicensePayload,
    pack_license_token,
    unpack_license_token,
)
from driving_eval.licensing.machine_id import (
    MachineFingerprint,
    get_current_machine_fingerprint,
    parse_fingerprint_dict,
)
from tools.admin_license_gen import (
    DEFAULT_VENDOR_PRIVATE_KEY_HEX,
    create_signed_license,
)


def test_ed25519_cryptographic_primitives():
    priv, pub = generate_keypair()
    assert len(priv) == 32
    assert len(pub) == 32

    # Derived public key matches
    derived_pub = publickey_from_private(priv)
    assert derived_pub == pub

    message = b"Offline Driving Evaluation System License Payload 2026"
    signature = sign(message, priv)
    assert len(signature) == 64

    # Verification must succeed with correct message and key
    assert verify(signature, message, pub) is True

    # Tampered message must fail
    tampered_message = b"Offline Driving Evaluation System License Payload 2027"
    assert verify(signature, tampered_message, pub) is False

    # Wrong public key must fail
    _, other_pub = generate_keypair()
    assert verify(signature, message, other_pub) is False

    # Corrupted signature must fail
    corrupted_sig = bytearray(signature)
    corrupted_sig[0] ^= 0x01
    assert verify(bytes(corrupted_sig), message, pub) is False


def test_machine_fingerprint_and_hardware_quorum():
    fp1 = get_current_machine_fingerprint()
    assert fp1.canonical_id.startswith("MCH-")
    assert len(fp1.canonical_id.split("-")) == 5

    # 1. Identical match (4/4 components)
    ok, matches = fp1.match(fp1)
    assert ok is True
    assert matches == 4

    # 2. Tolerance: replace 1 component (e.g. disk replaced) -> 3/4 matches -> Still VALID!
    fp_disk_replaced = MachineFingerprint(
        board_hash=fp1.board_hash,
        cpu_hash=fp1.cpu_hash,
        disk_hash="NEW_REPLACED_NVME_DISK_HASH_123456",
        mac_hash=fp1.mac_hash,
    )
    ok, matches = fp1.match(fp_disk_replaced)
    assert ok is True
    assert matches == 3

    # 3. Two components changed (e.g. disk + cpu) -> 2/4 matches -> REJECTED!
    fp_two_changed = MachineFingerprint(
        board_hash=fp1.board_hash,
        cpu_hash="DIFFERENT_CPU_ID_HASH_999999",
        disk_hash="NEW_REPLACED_NVME_DISK_HASH_123456",
        mac_hash=fp1.mac_hash,
    )
    ok, matches = fp1.match(fp_two_changed)
    assert ok is False
    assert matches == 2

    # 4. Completely different machine -> 0/4 matches -> REJECTED!
    fp_other = MachineFingerprint("b1", "c1", "d1", "m1")
    ok, matches = fp1.match(fp_other)
    assert ok is False
    assert matches == 0

    # Serialization
    d = fp1.to_dict()
    assert parse_fingerprint_dict(d) == fp1


def test_anti_clock_tampering_protection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_clock.db"
        guard = ClockTamperGuard(db_path=str(db_path), grace_seconds=30.0)

        t0 = 1700000000.0  # Base time
        guard.record_timestamp_anchor(current_time=t0)
        guard.record_timestamp_anchor(current_time=t0 + 100.0)
        guard.record_timestamp_anchor(current_time=t0 + 200.0)

        # 1. Normal forward time check
        res = guard.check_clock_validity(current_time=t0 + 250.0)
        assert res.valid is True
        assert res.historical_max_timestamp == t0 + 200.0

        # 2. Clock rollback attempt: current time set 10 hours back!
        res_rollback = guard.check_clock_validity(current_time=t0 - 36000.0)
        assert res_rollback.valid is False
        assert res_rollback.error == "CLOCK_ROLLBACK_DETECTED"

        # 3. Hash chain tampering attack: attacker edits timestamp in SQLite
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE clock_timeline SET timestamp = 1700000050.0 WHERE id = 2")
        conn.commit()
        conn.close()

        res_tampered = guard.check_clock_validity(current_time=t0 + 300.0)
        assert res_tampered.valid is False
        assert res_tampered.error in ("TIMELINE_RECORD_TAMPERED", "TIMELINE_CHAIN_BROKEN")


def test_token_packing_and_unpacking():
    payload = LicensePayload(
        car_id="CAR-UZ-01",
        machine_fingerprint={"board": "b_hash", "cpu": "c_hash", "disk": "d_hash", "mac": "m_hash"},
        issued_at="2026-10-06T12:00:00Z",
        expires_at="2027-12-31",
        tier="FULL",
        features=["4_cameras", "all_exercises"],
    )
    dummy_signature = b"\xaa" * 64
    token = pack_license_token(payload, dummy_signature)
    assert token.startswith("DRV-LIC-")

    recovered_payload, recovered_sig = unpack_license_token(token)
    assert recovered_payload["car_id"] == "CAR-UZ-01"
    assert recovered_payload["tier"] == "FULL"
    assert recovered_payload["expires_at"] == "2027-12-31"
    assert recovered_sig == dummy_signature


def test_admin_license_generation_and_validation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "driving_eval.db"
        lic_file = Path(tmp_dir) / "license.key"

        # Target machine fingerprint
        target_fp = MachineFingerprint("board_111", "cpu_222", "disk_333", "mac_444")

        # 1. Generate valid license via admin generator
        token = create_signed_license(
            car_id="CAR-UZ-01",
            fingerprint=target_fp,
            expires_at="2028-12-31",
            tier="FULL",
            private_key_hex=DEFAULT_VENDOR_PRIVATE_KEY_HEX,
        )

        manager = LicenseManager(
            public_key_hex=MASTER_PUBLIC_KEY_HEX,
            license_file_path=lic_file,
            db_path=str(db_path),
        )

        # 2. Validation with matching hardware & car_id
        res = manager.validate(
            token,
            expected_car_id="CAR-UZ-01",
            current_fingerprint=target_fp,
            test_now_timestamp=1760000000.0,
        )
        assert res.is_valid is True
        assert res.status_code == "ACTIVE"
        assert res.car_id == "CAR-UZ-01"
        assert res.tier == "FULL"
        assert res.matching_components == 4

        # 3. Validation with 1 swapped component (disk replaced) -> Must remain valid!
        fp_one_swapped = MachineFingerprint("board_111", "cpu_222", "disk_SWAPPED", "mac_444")
        res_swapped = manager.validate(
            token,
            expected_car_id="CAR-UZ-01",
            current_fingerprint=fp_one_swapped,
            test_now_timestamp=1760000000.0,
        )
        assert res_swapped.is_valid is True
        assert res_swapped.matching_components == 3

        # 4. Car ID mismatch
        res_car_mismatch = manager.validate(
            token,
            expected_car_id="CAR-UZ-02",
            current_fingerprint=target_fp,
        )
        assert res_car_mismatch.is_valid is False
        assert res_car_mismatch.status_code == "CAR_ID_MISMATCH"

        # 5. Machine mismatch (different computer)
        fp_alien = MachineFingerprint("alien_b", "alien_c", "alien_d", "alien_m")
        res_alien = manager.validate(
            token,
            expected_car_id="CAR-UZ-01",
            current_fingerprint=fp_alien,
        )
        assert res_alien.is_valid is False
        assert res_alien.status_code == "MACHINE_MISMATCH"

        # 6. Expired license validation
        token_expired = create_signed_license(
            car_id="CAR-UZ-01",
            fingerprint=target_fp,
            expires_at="2020-01-01",
            private_key_hex=DEFAULT_VENDOR_PRIVATE_KEY_HEX,
        )
        res_exp = manager.validate(
            token_expired,
            expected_car_id="CAR-UZ-01",
            current_fingerprint=target_fp,
            test_now_timestamp=1760000000.0,
        )
        assert res_exp.is_valid is False
        assert res_exp.status_code == "EXPIRED"

        # 7. Permanent license validation
        token_perm = create_signed_license(
            car_id="CAR-UZ-01",
            fingerprint=target_fp,
            expires_at="PERMANENT",
            private_key_hex=DEFAULT_VENDOR_PRIVATE_KEY_HEX,
        )
        res_perm = manager.validate(
            token_perm,
            expected_car_id="CAR-UZ-01",
            current_fingerprint=target_fp,
            test_now_timestamp=2000000000.0,
        )
        assert res_perm.is_valid is True
        assert res_perm.status_code == "ACTIVE"

        # 8. Stored file save and load
        manager.save_license_file(token)
        assert lic_file.exists()
        loaded_token = manager.load_license_file()
        assert loaded_token == token

        stored_res = manager.verify_stored_license(expected_car_id="CAR-UZ-01")
        # May fail hardware check if actual machine differs from target_fp, but verify method executes cleanly
        assert stored_res.status_code in ("ACTIVE", "MACHINE_MISMATCH")
