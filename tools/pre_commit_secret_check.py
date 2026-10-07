#!/usr/bin/env python3
"""Pre-commit Hook: Secret and Credential Scanner.

Scans staged changes to block accidental commits of:
- Cryptographic private keys (Ed25519, RSA, PEM)
- Known compromised keys (e.g. bdd0b1...)
- Hardcoded PIN backdoors (pin == "1234")
- Secrets, passwords, or authentication tokens
"""

import re
import subprocess
import sys
from pathlib import Path

BLOCKED_PATTERNS = [
    (
        "COMPROMISED_KEY",
        re.compile(r"bdd0b1a5fdd912b838c5cd6a6d08bc58caa1174c6f6a30df78cd157a1eb53869"),
        "Ma'lum bo'lgan kompromat dev kalit aniqlandi!",
    ),
    (
        "HARDCODED_PIN_BACKDOOR",
        re.compile(r'pin\s*==\s*["\']1234["\']|admin_pin\s*=\s*["\']1234["\']'),
        "Admin autentifikatsiyasida qattiq yozilgan 1234 PIN kodi aniqlandi!",
    ),
    (
        "PEM_PRIVATE_KEY",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"),
        "Xususiy kalit PEM fayli yoki siri aniqlandi!",
    ),
    (
        "GENERIC_SECRET_ASSIGNMENT",
        re.compile(r'(?i)(?:api_key|secret_key|private_key|auth_token)\s*=\s*["\'][A-Za-z0-9+/=_-]{16,}["\']'),
        "Qattiq yozilgan API kalit yoki sir aniqlandi!",
    ),
]

EXCLUDED_FILES = {
    "tools/pre_commit_secret_check.py",
    "tools/audit_git_secrets.py",
    "SECRETS_PURGE_GUIDE.md",
    "LICENSING.md",
    "AUDIT_REPORT.md",
    "FINAL_AUDIT_REPORT.md",
    "PROGRESS.md",
    "DECISIONS.md",
}


def get_staged_files() -> list[str]:
    res = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return []
    return [f.strip() for f in res.stdout.splitlines() if f.strip()]


def scan_file_content(file_path: str) -> list[tuple[str, int, str]]:
    violations = []
    p = Path(file_path)
    if not p.is_file():
        return []

    # Skip excluded documentation and scanner scripts
    if file_path.replace("\\", "/") in EXCLUDED_FILES:
        return []

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    for line_idx, line in enumerate(content.splitlines(), start=1):
        for name, regex, msg in BLOCKED_PATTERNS:
            if regex.search(line):
                violations.append((name, line_idx, msg))

    return violations


def main() -> int:
    staged = get_staged_files()
    if not staged:
        # If running manually without staged files, check all tracked files
        res = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=False,
        )
        staged = [f.strip() for f in res.stdout.splitlines() if f.strip()]

    all_violations = []
    for f in staged:
        file_violations = scan_file_content(f)
        for name, line, msg in file_violations:
            all_violations.append((f, line, name, msg))

    if all_violations:
        print("\n" + "!" * 80)
        print("[XAVFSIZLIK TO'SIg'I] PRE-COMMIT SIR VA XAVFSIZLIK TEKSHIRUVI XATOLIK BERDI!")
        print("Quyidagi fayllarda maxfiy ma'lumotlar yoki xavfsizlik zaifliklari aniqlandi:")
        print("!" * 80)
        for f, line, name, msg in all_violations:
            print(f" - {f}:{line} [{name}]: {msg}")
        print("!" * 80)
        print("Commit to'xtatildi. Iltimos, xususiy kalit yoki sirlarni olib tashlang.\n")
        return 1

    print("[OK] Pre-commit sir skaneri: Maxfiy kalit va sirlar topilmadi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
