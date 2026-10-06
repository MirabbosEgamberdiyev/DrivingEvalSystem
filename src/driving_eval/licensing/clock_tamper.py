"""Anti-clock-tampering protection using SQLite cryptographic timestamp chains.

Protects against offline license expiration bypass where a user turns back
the Windows operating system clock. Maintains a cryptographic SHA-256 chain
of observed historical timestamps and rejects system boots or tests where
the current clock is earlier than past committed records.
"""

import hashlib
import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger("driving_eval.licensing.clock")


@dataclass
class ClockCheckResult:
    valid: bool
    error: str | None = None
    historical_max_timestamp: float = 0.0
    current_timestamp: float = 0.0


class ClockTamperGuard:
    """Manages cryptographic timeline verification and rollback detection."""

    def __init__(self, db_path: str = "data/db/driving_eval.db", grace_seconds: float = 60.0):
        self.db_path = str(db_path)
        self.grace_seconds = grace_seconds
        self._ensure_tables()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_tables(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS clock_timeline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    recorded_iso TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    current_hash TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def record_timestamp_anchor(self, current_time: float | None = None) -> str:
        """Records a new verified timestamp anchor into the cryptographic timeline."""
        ts = current_time if current_time is not None else time.time()
        iso = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(ts))

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_hash FROM clock_timeline ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = row["current_hash"] if row else "GENESIS_ANCHOR_0000000000000000"

            h_in = f"{ts:.3f}:{prev_hash}".encode()
            cur_hash = hashlib.sha256(h_in).hexdigest()

            cursor.execute(
                """
                INSERT INTO clock_timeline (timestamp, recorded_iso, prev_hash, current_hash)
                VALUES (?, ?, ?, ?)
                """,
                (ts, iso, prev_hash, cur_hash),
            )
            conn.commit()
            return cur_hash

    def check_clock_validity(self, current_time: float | None = None) -> ClockCheckResult:
        """Verifies that the operating system clock has not been set backwards."""
        now_ts = current_time if current_time is not None else time.time()

        with self._connection() as conn:
            cursor = conn.cursor()

            # 1. Check max timestamp from clock_timeline
            cursor.execute("SELECT MAX(timestamp) as max_ts FROM clock_timeline")
            row = cursor.fetchone()
            max_timeline = float(row["max_ts"]) if row and row["max_ts"] is not None else 0.0

            # 2. Check max timestamp from exam_sessions if table exists
            max_session = 0.0
            try:
                cursor.execute("SELECT MAX(start_time) as max_start FROM exam_sessions")
                s_row = cursor.fetchone()
                if s_row and s_row["max_start"] is not None:
                    max_session = float(s_row["max_start"])
            except sqlite3.OperationalError:
                pass

            historical_max = max(max_timeline, max_session)

            # If current time is earlier than historical max (beyond grace period), rollback detected!
            if historical_max > 0.0 and (now_ts < (historical_max - self.grace_seconds)):
                msg = (
                    f"Tizim soati orqaga surilganligi aniqlandi! "
                    f"Hozirgi vaqt: {now_ts:.0f}, Oxirgi qayd: {historical_max:.0f}"
                )
                logger.critical(msg)
                return ClockCheckResult(
                    valid=False,
                    error="CLOCK_ROLLBACK_DETECTED",
                    historical_max_timestamp=historical_max,
                    current_timestamp=now_ts,
                )

            # 3. Verify cryptographic hash chain integrity of clock_timeline
            cursor.execute("SELECT id, timestamp, prev_hash, current_hash FROM clock_timeline ORDER BY id ASC")
            records = cursor.fetchall()
            expected_prev = "GENESIS_ANCHOR_0000000000000000"

            for r in records:
                if r["prev_hash"] != expected_prev:
                    return ClockCheckResult(
                        valid=False,
                        error="TIMELINE_CHAIN_BROKEN",
                        historical_max_timestamp=historical_max,
                        current_timestamp=now_ts,
                    )
                calc_hash = hashlib.sha256(f"{r['timestamp']:.3f}:{expected_prev}".encode()).hexdigest()
                if calc_hash != r["current_hash"]:
                    return ClockCheckResult(
                        valid=False,
                        error="TIMELINE_RECORD_TAMPERED",
                        historical_max_timestamp=historical_max,
                        current_timestamp=now_ts,
                    )
                expected_prev = r["current_hash"]

        return ClockCheckResult(
            valid=True,
            historical_max_timestamp=historical_max,
            current_timestamp=now_ts,
        )
