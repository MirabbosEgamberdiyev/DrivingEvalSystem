"""CSV export for driving examination sessions and violations."""

import csv
from pathlib import Path
from typing import Any


def export_violations_to_csv(
    output_path: str | Path,
    session_data: dict[str, Any],
    violations: list[dict[str, Any]],
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["session_id", "student_id", "rule_code", "status", "penalty", "confidence", "camera", "exercise", "timestamp", "description"])
        for v in violations:
            writer.writerow([
                session_data.get("id", ""),
                session_data.get("student_id", ""),
                v.get("rule_code", ""),
                v.get("status", ""),
                v.get("penalty", 0),
                v.get("confidence", 0.0),
                v.get("camera", ""),
                v.get("exercise", ""),
                v.get("timestamp", ""),
                v.get("description", ""),
            ])
    return out
