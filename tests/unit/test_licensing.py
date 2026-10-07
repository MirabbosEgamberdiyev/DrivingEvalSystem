"""Unit and integration tests for Ed25519 offline licensing, activation states, and anti-tamper security."""

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
from tools.admin_license_gen import create_signed_license


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

        # Ephemeral test keypair for clean, decoupled verification
        test_priv, test_pub = generate_keypair()
        target_fp = MachineFingerprint("board_111", "cpu_222", "disk_333", "mac_444")

        # 1. Generate valid license via admin generator
        token = create_signed_license(
            car_id="CAR-UZ-01",
            fingerprint=target_fp,
            expires_at="2028-12-31",
            tier="FULL",
            private_key_hex=test_priv.hex(),
        )

        manager = LicenseManager(
            public_key_hex=test_pub.hex(),
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

        # 4. Permanent license validation
        token_perm = create_signed_license(
            car_id="CAR-UZ-01",
            fingerprint=target_fp,
            expires_at="PERMANENT",
            private_key_hex=test_priv.hex(),
        )
        res_perm = manager.validate(
            token_perm,
            expected_car_id="CAR-UZ-01",
            current_fingerprint=target_fp,
            test_now_timestamp=2000000000.0,
        )
        assert res_perm.is_valid is True
        assert res_perm.status_code == "ACTIVE"

        # 5. Stored file save and load
        manager.save_license_file(token)
        assert lic_file.exists()
        loaded_token = manager.load_license_file()
        assert loaded_token == token

        stored_res = manager.verify_stored_license(expected_car_id="CAR-UZ-01")
        assert stored_res.status_code in ("ACTIVE", "MACHINE_MISMATCH")


# --- Comprehensive 9+ Activation Error Case Tests ---


def test_activation_case_1_valid():
    """Case 1: Standard valid license matches machine and car_id."""
    test_priv, test_pub = generate_keypair()
    fp = MachineFingerprint("b1", "c1", "d1", "m1")
    token = create_signed_license("CAR-01", fp, expires_at="2028-12-31", private_key_hex=test_priv.hex())
    manager = LicenseManager(public_key_hex=test_pub.hex())
    res = manager.validate(token, expected_car_id="CAR-01", current_fingerprint=fp, test_now_timestamp=1760000000.0)
    assert res.is_valid is True
    assert res.status_code == "ACTIVE"


def test_activation_case_2_forged_signature():
    """Case 2: Token signed by an attacker with an unauthorized private key."""
    _, legit_pub = generate_keypair()
    attacker_priv, _ = generate_keypair()
    fp = MachineFingerprint("b1", "c1", "d1", "m1")
    forged_token = create_signed_license("CAR-01", fp, expires_at="2028-12-31", private_key_hex=attacker_priv.hex())

    manager = LicenseManager(public_key_hex=legit_pub.hex())
    res = manager.validate(forged_token, expected_car_id="CAR-01", current_fingerprint=fp)
    assert res.is_valid is False
    assert res.status_code == "INVALID_SIGNATURE"


def test_activation_case_3_altered_payload():
    """Case 3: Attacker alters payload (e.g. tier changed to FULL) with original signature."""
    priv, pub = generate_keypair()
    fp = MachineFingerprint("b1", "c1", "d1", "m1")
    token = create_signed_license("CAR-01", fp, expires_at="2028-12-31", tier="TRAINING", private_key_hex=priv.hex())

    payload, sig = unpack_license_token(token)
    payload["tier"] = "FULL"  # Tampered field!
    tampered_payload_obj = LicensePayload(
        car_id=payload["car_id"],
        machine_fingerprint=payload["machine_fingerprint"],
        issued_at=payload["issued_at"],
        expires_at=payload["expires_at"],
        tier=payload["tier"],
        features=payload["features"],
    )
    tampered_token = pack_license_token(tampered_payload_obj, sig)

    manager = LicenseManager(public_key_hex=pub.hex())
    res = manager.validate(tampered_token, expected_car_id="CAR-01", current_fingerprint=fp)
    assert res.is_valid is False
    assert res.status_code == "INVALID_SIGNATURE"


def test_activation_case_4_expired():
    """Case 4: License expired in the past."""
    priv, pub = generate_keypair()
    fp = MachineFingerprint("b1", "c1", "d1", "m1")
    token = create_signed_license("CAR-01", fp, expires_at="2020-01-01", private_key_hex=priv.hex())
    manager = LicenseManager(public_key_hex=pub.hex())
    res = manager.validate(token, expected_car_id="CAR-01", current_fingerprint=fp, test_now_timestamp=1760000000.0)
    assert res.is_valid is False
    assert res.status_code == "EXPIRED"


def test_activation_case_5_machine_mismatch():
    """Case 5: License belongs to another vehicle computer."""
    priv, pub = generate_keypair()
    fp_car_a = MachineFingerprint("b_a", "c_a", "d_a", "m_a")
    fp_car_b = MachineFingerprint("b_b", "c_b", "d_b", "m_b")
    token = create_signed_license("CAR-01", fp_car_a, expires_at="2028-12-31", private_key_hex=priv.hex())
    manager = LicenseManager(public_key_hex=pub.hex())
    res = manager.validate(token, expected_car_id="CAR-01", current_fingerprint=fp_car_b, test_now_timestamp=1760000000.0)
    assert res.is_valid is False
    assert res.status_code == "MACHINE_MISMATCH"


def test_activation_case_6_clock_rollback():
    """Case 6: System clock rolled back into the past."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "clock.db"
        guard = ClockTamperGuard(db_path=str(db_path))
        t0 = 1750000000.0
        guard.record_timestamp_anchor(current_time=t0)

        priv, pub = generate_keypair()
        fp = MachineFingerprint("b1", "c1", "d1", "m1")
        token = create_signed_license("CAR-01", fp, expires_at="2028-12-31", private_key_hex=priv.hex())
        manager = LicenseManager(public_key_hex=pub.hex(), clock_guard=guard)

        # Roll back time by 10 days
        res = manager.validate(token, expected_car_id="CAR-01", current_fingerprint=fp, test_now_timestamp=t0 - 864000.0)
        assert res.is_valid is False
        assert res.status_code == "CLOCK_ROLLBACK"


def test_activation_case_7_empty_key():
    """Case 7: Empty key string or whitespace."""
    _, pub = generate_keypair()
    manager = LicenseManager(public_key_hex=pub.hex())
    for empty_input in ["", "   ", "\n\t"]:
        res = manager.validate(empty_input)
        assert res.is_valid is False
        assert res.status_code == "MALFORMED"


def test_activation_case_8_corrupted_format():
    """Case 8: Corrupted base64 or garbage data."""
    _, pub = generate_keypair()
    manager = LicenseManager(public_key_hex=pub.hex())
    for bad in ["DRV-LIC-NOT-BASE64!@#$%", "DRV-LIC-QUFB", "DRV-LIC-"]:
        res = manager.validate(bad)
        assert res.is_valid is False
        assert res.status_code == "MALFORMED"


def test_activation_case_9_car_id_mismatch():
    """Case 9: License issued for CAR-01 presented on CAR-02."""
    priv, pub = generate_keypair()
    fp = MachineFingerprint("b1", "c1", "d1", "m1")
    token = create_signed_license("CAR-01", fp, expires_at="2028-12-31", private_key_hex=priv.hex())
    manager = LicenseManager(public_key_hex=pub.hex())
    res = manager.validate(token, expected_car_id="CAR-02", current_fingerprint=fp, test_now_timestamp=1760000000.0)
    assert res.is_valid is False
    assert res.status_code == "CAR_ID_MISMATCH"


def test_exam_start_blocked_without_active_license():
    """Case 10 (Gating): Exam start must strictly fail when application is UNLICENSED."""
    from driving_eval.core.state_machine import (
        ApplicationState,
        ApplicationStateMachine,
        ExamState,
        ExamStateMachine,
        InvalidStateTransitionError,
    )

    app_sm = ApplicationStateMachine()
    exam_sm = ExamStateMachine(initial_state=ExamState.READY, app_state_machine=app_sm)

    # Application is UNLICENSED
    assert app_sm.current_state == ApplicationState.UNLICENSED

    # Starting exam when app is UNLICENSED must be blocked
    assert not exam_sm.can_transition(ExamState.PRECHECK)
    try:
        exam_sm.transition_to(ExamState.PRECHECK, "Exam start attempt")
        unlicensed_blocked = False
    except InvalidStateTransitionError as ex:
        unlicensed_blocked = True
        assert "UNLICENSED" in str(ex)

    assert unlicensed_blocked is True
    assert exam_sm.current_state == ExamState.READY
