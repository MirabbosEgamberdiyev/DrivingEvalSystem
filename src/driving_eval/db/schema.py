"""SQLite database schema definitions and pragmas.

Ensures strict constraints, WAL journal mode for crash resistance, and tamper-evident tables.
"""

PRAGMAS = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
"""

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id TEXT PRIMARY KEY,
    passport_id TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    phone TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vehicles (
    id TEXT PRIMARY KEY,
    car_id TEXT UNIQUE NOT NULL,
    vin TEXT NOT NULL,
    plate_number TEXT NOT NULL,
    model TEXT NOT NULL,
    manufacture_year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cameras (
    name TEXT PRIMARY KEY,
    device_index INTEGER NOT NULL,
    resolution TEXT NOT NULL,
    fps INTEGER NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS camera_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    fps REAL NOT NULL,
    dropped_frames INTEGER NOT NULL,
    drift_px REAL NOT NULL,
    is_healthy INTEGER NOT NULL,
    FOREIGN KEY(camera_name) REFERENCES cameras(name)
);

CREATE TABLE IF NOT EXISTS exercises (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    sequence_order INTEGER NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS rules (
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    screen_text TEXT NOT NULL,
    voice_file TEXT NOT NULL,
    voice_text TEXT NOT NULL,
    penalty INTEGER NOT NULL,
    critical INTEGER NOT NULL,
    rules_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS test_sessions (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL,
    vehicle_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL, -- 'IN_PROGRESS', 'COMPLETED', 'TERMINATED', 'INTERRUPTED'
    mode TEXT NOT NULL DEFAULT 'ASSESSMENT', -- 'TRAINING' or 'ASSESSMENT'
    language TEXT NOT NULL DEFAULT 'uz-Latn', -- 'uz-Latn', 'uz-Cyrl', 'ru'
    score INTEGER NOT NULL,
    total_penalty INTEGER NOT NULL,
    result TEXT, -- 'PASS', 'FAIL', 'INCOMPLETE'
    rules_version TEXT NOT NULL,
    app_version TEXT NOT NULL,
    session_hash TEXT,
    FOREIGN KEY(student_id) REFERENCES students(id),
    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS violations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'CONFIRMED' or 'SUSPECT'
    confidence REAL NOT NULL,
    camera TEXT NOT NULL,
    exercise TEXT NOT NULL,
    rule_code TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    description TEXT NOT NULL,
    evidence_id TEXT,
    FOREIGN KEY(session_id) REFERENCES test_sessions(id),
    FOREIGN KEY(rule_code) REFERENCES rules(code)
);

CREATE TABLE IF NOT EXISTS penalties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    violation_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    points_deducted INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(violation_id) REFERENCES violations(id),
    FOREIGN KEY(session_id) REFERENCES test_sessions(id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    violation_id TEXT,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL, -- 'IMAGE', 'VIDEO', 'JSON'
    sha256_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES test_sessions(id)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    current_score INTEGER NOT NULL,
    total_penalty INTEGER NOT NULL,
    critical_count INTEGER NOT NULL,
    FOREIGN KEY(session_id) REFERENCES test_sessions(id)
);

CREATE TABLE IF NOT EXISTS test_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT UNIQUE NOT NULL,
    final_score INTEGER NOT NULL,
    result TEXT NOT NULL, -- 'PASS' or 'FAIL'
    critical_violations_count INTEGER NOT NULL,
    suspect_count INTEGER NOT NULL,
    hash_chain_root TEXT NOT NULL,
    finalized_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES test_sessions(id)
);

CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    module TEXT NOT NULL,
    message TEXT NOT NULL,
    session_id TEXT,
    state TEXT
);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    admin_user TEXT NOT NULL,
    action TEXT NOT NULL,
    target TEXT,
    details TEXT,
    ip_or_tty TEXT NOT NULL
);

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

CREATE TABLE IF NOT EXISTS consent_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    eula_version TEXT NOT NULL,
    agreed INTEGER NOT NULL,
    ip_or_device TEXT NOT NULL,
    FOREIGN KEY(student_id) REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_violations_session ON violations(session_id);
CREATE INDEX IF NOT EXISTS idx_evidence_session ON evidence(session_id);
CREATE INDEX IF NOT EXISTS idx_system_logs_session ON system_logs(session_id);
"""
