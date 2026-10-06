"""CSV export for driving examination sessions and violations across 3 languages."""

import csv
from pathlib import Path
from typing import Any

CSV_HEADERS = {
    "uz-Latn": ["session_id", "student_id", "rule_code", "status", "penalty", "confidence", "camera", "exercise", "timestamp", "description"],
    "uz-Cyrl": ["сессия_ид", "талаба_ид", "қоида_коди", "ҳолат", "жарима", "ишонч", "камера", "машқ", "вақт", "тавсиф"],
    "ru": ["ид_сессии", "ид_студента", "код_правила", "статус", "штраф", "доверие", "камера", "упражнение", "время", "описание"],
}


def export_violations_to_csv(
    output_path: str | Path,
    session_data: dict[str, Any],
    violations: list[dict[str, Any]],
    language: str = "uz-Latn",
) -> Path:
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    header = CSV_HEADERS.get(language, CSV_HEADERS["uz-Latn"])

    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for v in violations:
            writer.writerow([
                session_data.get("id", ""),
                session_data.get("student_id", ""),
                v.get("rule_code", ""),
                v.get("status", ""),
                v.get("penalty", 0),
                round(float(v.get("confidence", 0.0)), 3),
                v.get("camera", ""),
                v.get("exercise", ""),
                str(v.get("timestamp", ""))[:19],
                v.get("details", v.get("description", "")),
            ])
    return out
