"""Database migration runner.

Applies schema migrations idempotently and ensures database integrity.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime

from driving_eval.db.schema import CREATE_TABLES_SQL, PRAGMAS

logger = logging.getLogger("driving_eval.db.migrations")


def _apply_migration_2(conn: sqlite3.Connection) -> None:
    """Applies migration 2: adds mode/language to test_sessions and new tables."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(test_sessions)")
    columns = {row[1] for row in cursor.fetchall()}

    if "mode" not in columns:
        cursor.execute(
            "ALTER TABLE test_sessions ADD COLUMN mode TEXT NOT NULL DEFAULT 'ASSESSMENT'"
        )
    if "language" not in columns:
        cursor.execute(
            "ALTER TABLE test_sessions ADD COLUMN language TEXT NOT NULL DEFAULT 'uz-Latn'"
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS license_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            license_key TEXT NOT NULL,
            machine_id TEXT NOT NULL,
            issued_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            features TEXT NOT NULL,
            signature TEXT NOT NULL,
            last_verified_at TEXT NOT NULL,
            anti_clock_max_timestamp TEXT NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consent_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            eula_version TEXT NOT NULL,
            agreed INTEGER NOT NULL,
            ip_or_device TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES students(id)
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)


def _apply_migration_3(conn: sqlite3.Connection) -> None:
    """Applies migration 3: adds root_signature column to test_results."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(test_results)")
    columns = {row[1] for row in cursor.fetchall()}
    if "root_signature" not in columns:
        cursor.execute("ALTER TABLE test_results ADD COLUMN root_signature TEXT;")


def _apply_migration_4(conn: sqlite3.Connection) -> None:
    """Applies migration 4: creates session_hash_ledger for monotonic cryptographic chain."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_hash_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            payload TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES test_sessions(id)
        );
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hash_ledger_sess_seq ON session_hash_ledger(session_id, seq);
    """)


MIGRATIONS: list[tuple[int, str, str | Callable[[sqlite3.Connection], None]]] = [
    (1, "Initial baseline tables with foreign keys and WAL mode", CREATE_TABLES_SQL),
    (2, "Add mode, language, license_state, consent_log, app_settings", _apply_migration_2),
    (3, "Add root_signature to test_results for cryptographic tamper detection", _apply_migration_3),
    (4, "Add session_hash_ledger for monotonic cryptographic chain", _apply_migration_4),
]


def run_migrations(conn: sqlite3.Connection) -> None:
    """Applies all pending migrations within a transaction."""
    # Execute pragmas
    conn.executescript(PRAGMAS)

    # Ensure schema_migrations table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        );
    """)
    conn.commit()

    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations")
    applied = {row[0] for row in cursor.fetchall()}

    for version, desc, handler in MIGRATIONS:
        if version not in applied:
            logger.info("Migratsiya bajarilmoqda v%d: %s", version, desc)
            try:
                if callable(handler):
                    handler(conn)
                else:
                    conn.executescript(handler)

                now_iso = datetime.now(UTC).isoformat()
                conn.execute(
                    "INSERT INTO schema_migrations (version, applied_at, description) VALUES (?, ?, ?)",
                    (version, now_iso, desc),
                )
                conn.commit()
                logger.info("Migratsiya v%d muvaffaqiyatli qo'llandi.", version)
            except Exception as e:
                conn.rollback()
                logger.error("Migratsiya v%d da xato yuz berdi: %s", version, e)
                raise
