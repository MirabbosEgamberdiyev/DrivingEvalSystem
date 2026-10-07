"""Unit tests for SQLite database repository, migrations, and SHA-256 hash chaining."""

import pytest

from driving_eval.db.repository import DatabaseRepository


@pytest.fixture
def repo(tmp_path):
    db_file = tmp_path / "test_eval.db"
    return DatabaseRepository(db_file)


def test_db_initialization_and_wal_mode(repo):
    with repo.get_connection() as conn:
        cursor = conn.execute("PRAGMA journal_mode;")
        row = cursor.fetchone()
        assert row[0].upper() == "WAL"

        cursor = conn.execute("SELECT count(*) FROM schema_migrations;")
        count = cursor.fetchone()[0]
        assert count >= 1


def test_session_lifecycle_and_hash_chain(repo):
    student_id = repo.register_or_get_student("AA1234567", "Ali", "Valiyev")
    vehicle_id = repo.register_vehicle("CAR-01", "VIN12345", "01A777AA", "Cobalt", 2024)

    session_id = "SESS-20261006-001"
    repo.sync_rules("config/rules.yaml")
    repo.create_session(
        session_id=session_id,
        student_id=student_id,
        vehicle_id=vehicle_id,
        start_score=100,
        rules_version="1.0.0",
        app_version="1.0.0",
    )

    sess = repo.get_session(session_id)
    assert sess is not None
    assert sess["status"] == "IN_PROGRESS"
    assert sess["score"] == 100
    initial_hash = sess["session_hash"]
    assert len(initial_hash) == 64

    # Record first violation
    v1_id = "VIOL-001"
    repo.record_violation(
        violation_id=v1_id,
        session_id=session_id,
        status="CONFIRMED",
        confidence=0.95,
        camera="FRONT",
        exercise="ZMEIKA",
        rule_code="CONE_TOUCH",
        description="Chap konusga tegilishi qayd etildi",
    )
    repo.record_penalty(violation_id=v1_id, session_id=session_id, points=25)

    sess_after_v1 = repo.get_session(session_id)
    assert sess_after_v1["score"] == 75
    assert sess_after_v1["total_penalty"] == 25
    # Hash must have changed (chained)
    assert sess_after_v1["session_hash"] != initial_hash

    # Finalize test
    root_hash = repo.finalize_test_result(
        session_id=session_id,
        final_score=75,
        result="FAIL",
        critical_count=0,
        suspect_count=0,
    )
    assert len(root_hash) == 64
    assert repo.verify_session_hash_integrity(session_id) is True

    final_sess = repo.get_session(session_id)
    assert final_sess["status"] == "COMPLETED"
    assert final_sess["result"] == "FAIL"


def test_interrupted_session_handling(repo):
    student_id = repo.register_or_get_student("BB9999999", "Olim", "Karimov")
    vehicle_id = repo.register_vehicle("CAR-02", "VIN99999", "01B999BB", "Lacetti", 2023)
    session_id = "SESS-CRASH-001"

    repo.create_session(session_id, student_id, vehicle_id, 100, "1.0", "1.0")
    unfinished = repo.get_unfinished_sessions()
    assert len(unfinished) == 1
    assert unfinished[0]["id"] == session_id

    # Simulate crash recovery
    repo.close_interrupted_session(session_id, reason="POWER_LOSS_REBOOT")
    unfinished_after = repo.get_unfinished_sessions()
    assert len(unfinished_after) == 0

    sess = repo.get_session(session_id)
    assert sess["status"] == "INTERRUPTED"
    assert sess["result"] == "INCOMPLETE"


def test_tampered_violation_breaks_hash_integrity(repo):
    repo.sync_rules("config/rules.yaml")
    student_id = repo.register_or_get_student("CC8888888", "Aziz", "Sultonov")
    vehicle_id = repo.register_vehicle("CAR-03", "VIN88888", "01C888CC", "Cobalt", 2024)
    session_id = "SESS-TAMPER-001"


    repo.create_session(session_id, student_id, vehicle_id, 100, "1.0", "1.0")
    v_id = "V-TAMPER-01"
    repo.record_violation(
        violation_id=v_id,
        session_id=session_id,
        status="CONFIRMED",
        confidence=0.98,
        camera="FRONT",
        exercise="ZMEIKA",
        rule_code="CONE_TOUCH",
        description="Konusga tegildi",
    )
    repo.record_penalty(violation_id=v_id, session_id=session_id, points=25)
    repo.finalize_test_result(
        session_id=session_id,
        final_score=75,
        result="FAIL",
        critical_count=0,
        suspect_count=0,
    )

    # Initial untampered state MUST pass
    assert repo.verify_session_hash_integrity(session_id) is True

    # Tamper 1: modify violation rule_code directly in DB
    with repo.get_connection() as conn:
        conn.execute("UPDATE violations SET rule_code = 'SEATBELT_UNFASTENED' WHERE id = ?", (v_id,))
        conn.commit()

    # Must detect tampering!
    assert repo.verify_session_hash_integrity(session_id) is False



    # Restore violation, but tamper with test_results final_score
    with repo.get_connection() as conn:
        conn.execute("UPDATE violations SET rule_code = 'CONE_TOUCH' WHERE id = ?", (v_id,))
        conn.execute("UPDATE test_results SET final_score = 100 WHERE session_id = ?", (session_id,))
        conn.commit()

    # Must detect tampered score!
    assert repo.verify_session_hash_integrity(session_id) is False

