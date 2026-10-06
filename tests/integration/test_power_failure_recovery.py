"""Integration test for power cutoff detection and graceful session recovery on boot."""


from driving_eval.db.repository import DatabaseRepository
from driving_eval.maintenance.session_recovery import SessionRecoveryService


def test_power_failure_recovery_on_reboot(tmp_path):
    db_path = tmp_path / "power_cut.db"
    repo = DatabaseRepository(db_path)
    repo.sync_rules("config/rules.yaml")

    # 1. Start an active session
    stu_id = repo.register_or_get_student("PWR123", "Rustam", "Qodirov")
    veh_id = repo.register_vehicle("CAR-PWR", "VINPWR", "01PWR", "Cobalt", 2024)
    sess_id = "SESS-PWR-CUT-01"

    repo.create_session(sess_id, stu_id, veh_id, 100, "1.0.0", "1.0.0")

    # Simulate active violation right before power cut
    repo.record_violation(
        violation_id="VIOL-PWR-01",
        session_id=sess_id,
        status="CONFIRMED",
        confidence=0.95,
        camera="FRONT",
        exercise="START",
        rule_code="SEATBELT_UNFASTENED",
        description="Kamar taqilmagan",
    )
    repo.record_penalty("VIOL-PWR-01", sess_id, 10)

    # Abrupt power cut! Process dies here. Session is left IN_PROGRESS in SQLite WAL.
    unfinished = repo.get_unfinished_sessions()
    assert len(unfinished) == 1
    assert unfinished[0]["id"] == sess_id
    assert unfinished[0]["status"] == "IN_PROGRESS"

    # 2. Vehicle engine restarts, system boots up
    recovery_service = SessionRecoveryService(repo, mode="SAFE_INTERRUPT")
    recovered = recovery_service.check_and_recover_on_boot()

    assert len(recovered) == 1
    assert recovered[0]["id"] == sess_id

    # Verify session is now safely finalized as INTERRUPTED
    sess_after = repo.get_session(sess_id)
    assert sess_after["status"] == "INTERRUPTED"
    assert sess_after["result"] == "INCOMPLETE"
    assert sess_after["finished_at"] is not None
    # Score must reflect what was recorded up to the power cut
    assert sess_after["score"] == 90
    assert sess_after["total_penalty"] == 10

    # Ensure no unfinished sessions remain
    assert len(repo.get_unfinished_sessions()) == 0
