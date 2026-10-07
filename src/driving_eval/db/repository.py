"""Database repository implementing immediate commits, audit logs, and SHA-256 hash chaining.

Prevents silent failures and guarantees tamper evidence across test records.
"""

import hashlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from driving_eval.db.migrations import run_migrations
from driving_eval.db.schema import PRAGMAS


class DatabaseRepository:
    """Manages SQLite access with WAL mode and cryptographically verified event records."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.executescript(PRAGMAS)
        return conn

    def _init_db(self) -> None:
        with self.get_connection() as conn:
            run_migrations(conn)

    def sync_rules(self, rules_manifest_path_or_obj: Any) -> None:
        """Populates the rules table from rules.yaml manifest."""
        from driving_eval.core.config_schema import RulesManifest
        if isinstance(rules_manifest_path_or_obj, (str, Path)):
            manifest = RulesManifest.load_from_yaml(rules_manifest_path_or_obj)
        else:
            manifest = rules_manifest_path_or_obj

        with self.get_connection() as conn:
            for rule in manifest.rules:
                conn.execute(
                    """
                    INSERT INTO rules (
                        code, title, screen_text, voice_file, voice_text,
                        penalty, critical, rules_version
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(code) DO UPDATE SET
                        title=excluded.title,
                        screen_text=excluded.screen_text,
                        voice_file=excluded.voice_file,
                        voice_text=excluded.voice_text,
                        penalty=excluded.penalty,
                        critical=excluded.critical,
                        rules_version=excluded.rules_version;
                    """,
                    (
                        rule.code,
                        rule.title,
                        rule.screen_text,
                        rule.voice_file,
                        rule.voice_text,
                        rule.penalty,
                        1 if rule.critical else 0,
                        manifest.version,
                    ),
                )
            conn.commit()

    @staticmethod
    def compute_sha256(data_bytes: bytes) -> str:
        """Returns standard hex SHA-256 hash of bytes."""
        return hashlib.sha256(data_bytes).hexdigest()

    @staticmethod
    def compute_file_sha256(file_path: str | Path) -> str:
        """Calculates SHA-256 hash of an existing file."""
        p = Path(file_path)
        if not p.exists():
            return ""
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    # --- Student & Vehicle Management ---

    def register_or_get_student(self, passport_id: str, first_name: str, last_name: str, phone: str = "") -> str:
        student_id = f"STU-{hashlib.md5(passport_id.encode()).hexdigest()[:8].upper()}"
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO students (id, passport_id, first_name, last_name, phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(passport_id) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    phone=excluded.phone;
                """,
                (student_id, passport_id, first_name, last_name, phone, now_iso),
            )
            conn.commit()
        return student_id

    def register_vehicle(self, car_id: str, vin: str, plate_number: str, model: str, year: int) -> str:
        v_id = f"VEH-{car_id}"
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO vehicles (id, car_id, vin, plate_number, model, manufacture_year)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(car_id) DO UPDATE SET
                    vin=excluded.vin,
                    plate_number=excluded.plate_number,
                    model=excluded.model,
                    manufacture_year=excluded.manufacture_year;
                """,
                (v_id, car_id, vin, plate_number, model, year),
            )
            conn.commit()
        return v_id

    # --- Session Management ---

    def create_session(
        self,
        session_id: str,
        student_id: str,
        vehicle_id: str,
        start_score: int,
        rules_version: str,
        app_version: str,
        mode: str = "ASSESSMENT",
        language: str = "uz-Latn",
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        initial_hash = self.compute_sha256(f"SESSION_START:{session_id}:{student_id}:{now_iso}".encode())
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO test_sessions (
                    id, student_id, vehicle_id, started_at, status, mode, language, score,
                    total_penalty, rules_version, app_version, session_hash
                ) VALUES (?, ?, ?, ?, 'IN_PROGRESS', ?, ?, ?, 0, ?, ?, ?);
                """,
                (session_id, student_id, vehicle_id, now_iso, mode, language, start_score, rules_version, app_version, initial_hash),
            )
            # Log initial score snapshot
            conn.execute(
                """
                INSERT INTO scores (session_id, timestamp, current_score, total_penalty, critical_count)
                VALUES (?, ?, ?, 0, 0);
                """,
                (session_id, now_iso, start_score),
            )
            conn.commit()

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM test_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_unfinished_sessions(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM test_sessions WHERE status = 'IN_PROGRESS'")
            return [dict(r) for r in cursor.fetchall()]

    def get_all_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT s.*, st.passport_id, st.first_name, st.last_name, v.plate_number, v.model
                FROM test_sessions s
                LEFT JOIN students st ON s.student_id = st.id
                LEFT JOIN vehicles v ON s.vehicle_id = v.id
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cursor.fetchall()]

    def close_interrupted_session(self, session_id: str, reason: str = "POWER_LOSS_DETECTED") -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                UPDATE test_sessions
                SET status = 'INTERRUPTED', finished_at = ?, result = 'INCOMPLETE'
                WHERE id = ?;
                """,
                (now_iso, session_id),
            )
            self.log_system_event(
                conn=conn,
                level="WARNING",
                module="db.recovery",
                message=f"Tizim uzilgan sessiyani yopdi ({reason})",
                session_id=session_id,
                state="INTERRUPTED",
            )
            conn.commit()

    # --- Violation and Hash-Chaining ---

    def record_violation(
        self,
        violation_id: str,
        session_id: str,
        status: str,  # 'CONFIRMED' or 'SUSPECT'
        confidence: float,
        camera: str,
        exercise: str,
        rule_code: str,
        description: str,
        evidence_id: str | None = None,
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            # 1. Update hash chain
            cur = conn.execute("SELECT session_hash FROM test_sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            prev_hash = row["session_hash"] if row and row["session_hash"] else "INIT"
            event_payload = f"{prev_hash}|VIOLATION:{violation_id}:{status}:{rule_code}:{confidence:.3f}:{now_iso}"
            new_hash = self.compute_sha256(event_payload.encode())

            # 2. Insert violation
            conn.execute(
                """
                INSERT INTO violations (
                    id, session_id, status, confidence, camera, exercise,
                    rule_code, timestamp, description, evidence_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (violation_id, session_id, status, confidence, camera, exercise, rule_code, now_iso, description, evidence_id),
            )

            # 3. Update session hash
            conn.execute("UPDATE test_sessions SET session_hash = ? WHERE id = ?", (new_hash, session_id))
            conn.commit()

    def record_penalty(self, violation_id: str, session_id: str, points: int) -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO penalties (violation_id, session_id, points_deducted, timestamp)
                VALUES (?, ?, ?, ?);
                """,
                (violation_id, session_id, points, now_iso),
            )
            conn.execute(
                """
                UPDATE test_sessions
                SET total_penalty = total_penalty + ?,
                    score = score - ?
                WHERE id = ?;
                """,
                (points, points, session_id),
            )
            conn.commit()

    def record_score_snapshot(
        self, session_id: str, current_score: int, total_penalty: int, critical_count: int
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO scores (session_id, timestamp, current_score, total_penalty, critical_count)
                VALUES (?, ?, ?, ?, ?);
                """,
                (session_id, now_iso, current_score, total_penalty, critical_count),
            )
            conn.commit()

    def record_evidence(
        self,
        evidence_id: str,
        session_id: str,
        violation_id: str | None,
        file_path: str,
        file_type: str,
        sha256_hash: str,
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO evidence (
                    id, session_id, violation_id, file_path, file_type, sha256_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (evidence_id, session_id, violation_id, file_path, file_type, sha256_hash, now_iso),
            )
            conn.commit()

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        """Retrieves evidence record by its primary key ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_evidence_by_violation(self, violation_id: str) -> list[dict[str, Any]]:
        """Retrieves all evidence records linked to a specific violation."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM evidence WHERE violation_id = ?", (violation_id,))
            return [dict(r) for r in cursor.fetchall()]

    def finalize_test_result(
        self,
        session_id: str,
        final_score: int,
        result: str,  # 'PASS' or 'FAIL'
        critical_count: int,
        suspect_count: int,
    ) -> str:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            cur = conn.execute("SELECT session_hash FROM test_sessions WHERE id = ?", (session_id,))
            row = cur.fetchone()
            session_hash = row["session_hash"] if row and row["session_hash"] else "EMPTY"
            final_root_hash = self.compute_sha256(
                f"{session_hash}|FINAL:{final_score}:{result}:{critical_count}:{now_iso}".encode()
            )

            conn.execute(
                """
                INSERT INTO test_results (
                    session_id, final_score, result, critical_violations_count,
                    suspect_count, hash_chain_root, finalized_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    final_score=excluded.final_score,
                    result=excluded.result,
                    critical_violations_count=excluded.critical_violations_count,
                    suspect_count=excluded.suspect_count,
                    hash_chain_root=excluded.hash_chain_root,
                    finalized_at=excluded.finalized_at;
                """,
                (session_id, final_score, result, critical_count, suspect_count, final_root_hash, now_iso),
            )

            status = "TERMINATED" if critical_count > 0 else "COMPLETED"
            conn.execute(
                """
                UPDATE test_sessions
                SET finished_at = ?, status = ?, score = ?, result = ?, session_hash = ?
                WHERE id = ?;
                """,
                (now_iso, status, final_score, result, final_root_hash, session_id),
            )
            conn.commit()
            return final_root_hash

    # --- System Logs and Audit ---

    def log_system_event(
        self,
        level: str,
        module: str,
        message: str,
        session_id: str | None = None,
        state: str | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        should_close = False
        if conn is None:
            conn = self.get_connection()
            should_close = True

        try:
            conn.execute(
                """
                INSERT INTO system_logs (timestamp, level, module, message, session_id, state)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (now_iso, level, module, message, session_id, state),
            )
            if should_close:
                conn.commit()
        finally:
            if should_close:
                conn.close()

    def log_admin_action(self, admin_user: str, action: str, target: str, details: str, ip_or_tty: str = "LOCAL") -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO admin_audit_log (timestamp, admin_user, action, target, details, ip_or_tty)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (now_iso, admin_user, action, target, details, ip_or_tty),
            )
            conn.commit()

    def get_violations_for_session(self, session_id: str) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT v.*, r.title, r.penalty, r.critical
                FROM violations v
                LEFT JOIN rules r ON v.rule_code = r.code
                WHERE v.session_id = ?
                ORDER BY v.timestamp ASC;
                """,
                (session_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    def verify_session_hash_integrity(self, session_id: str) -> bool:
        """Verifies if the stored root hash matches cryptographic recalculation of the entire session chain."""
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM test_results WHERE session_id = ?", (session_id,))
            res = cur.fetchone()
            if not res or not res["hash_chain_root"] or len(res["hash_chain_root"]) != 64:
                return False

            sess_cur = conn.execute("SELECT * FROM test_sessions WHERE id = ?", (session_id,))
            sess = sess_cur.fetchone()
            if not sess:
                return False

            # Recalculate hash chain from source of truth
            # 1. Base session start hash
            initial_payload = f"SESSION_START:{sess['id']}:{sess['student_id']}:{sess['started_at']}".encode()
            current_hash = self.compute_sha256(initial_payload)

            # 2. Iterate each violation in chronological insertion order
            v_cur = conn.execute(
                """
                SELECT id, status, rule_code, confidence, timestamp
                FROM violations
                WHERE session_id = ?
                ORDER BY timestamp ASC, id ASC
                """,
                (session_id,),
            )
            for row in v_cur.fetchall():
                payload = f"{current_hash}|VIOLATION:{row['id']}:{row['status']}:{row['rule_code']}:{row['confidence']:.3f}:{row['timestamp']}".encode()
                current_hash = self.compute_sha256(payload)

            # 3. Finalization hash
            final_payload = (
                f"{current_hash}|FINAL:{res['final_score']}:{res['result']}:{res['critical_violations_count']}:{res['finalized_at']}".encode()
            )
            expected_root_hash = self.compute_sha256(final_payload)

            return expected_root_hash == res["hash_chain_root"]


    # --- Consent & EULA ---

    def record_consent(
        self,
        student_id: str,
        eula_version: str,
        agreed: bool = True,
        ip_or_device: str = "TOUCHSCREEN",
    ) -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO consent_log (student_id, timestamp, eula_version, agreed, ip_or_device)
                VALUES (?, ?, ?, ?, ?);
                """,
                (student_id, now_iso, eula_version, 1 if agreed else 0, ip_or_device),
            )
            conn.commit()

    def has_valid_consent(self, student_id: str, eula_version: str) -> bool:
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                SELECT agreed FROM consent_log
                WHERE student_id = ? AND eula_version = ?
                ORDER BY timestamp DESC LIMIT 1;
                """,
                (student_id, eula_version),
            )
            row = cur.fetchone()
            return bool(row and row["agreed"] == 1)

    # --- License State ---

    def save_license_state(
        self,
        license_key: str,
        machine_id: str,
        issued_at: str,
        expires_at: str,
        features: list[str] | str,
        signature: str,
        anti_clock_max_timestamp: str,
    ) -> None:
        import json
        features_json = json.dumps(features) if isinstance(features, list) else str(features)
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO license_state (
                    id, license_key, machine_id, issued_at, expires_at,
                    features, signature, last_verified_at, anti_clock_max_timestamp
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    license_key=excluded.license_key,
                    machine_id=excluded.machine_id,
                    issued_at=excluded.issued_at,
                    expires_at=excluded.expires_at,
                    features=excluded.features,
                    signature=excluded.signature,
                    last_verified_at=excluded.last_verified_at,
                    anti_clock_max_timestamp=excluded.anti_clock_max_timestamp;
                """,
                (
                    license_key,
                    machine_id,
                    issued_at,
                    expires_at,
                    features_json,
                    signature,
                    now_iso,
                    anti_clock_max_timestamp,
                ),
            )
            conn.commit()

    def get_license_state(self) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT * FROM license_state WHERE id = 1;")
            row = cur.fetchone()
            return dict(row) if row else None

    # --- App Settings ---

    def set_app_setting(self, key: str, value: str) -> None:
        now_iso = datetime.now(UTC).isoformat()
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at;
                """,
                (key, value, now_iso),
            )
            conn.commit()

    def get_app_setting(self, key: str, default: str = "") -> str:
        with self.get_connection() as conn:
            cur = conn.execute("SELECT value FROM app_settings WHERE key = ?;", (key,))
            row = cur.fetchone()
            return str(row["value"]) if row else default

