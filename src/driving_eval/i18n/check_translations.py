"""Translation validation linter and review report generator.

Ensures:
1. 100% key parity across uz-Latn, uz-Cyrl, and ru catalogs.
2. Parameter placeholder consistency ({0}, {n}).
3. 100% 3-language completeness in config/rules.yaml.
4. Generates TRANSLATION_REVIEW.md for any unreviewed entries.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from driving_eval.i18n.service import SUPPORTED_LANGUAGES

PLACEHOLDER_REGEX = re.compile(r"\{[a-zA-Z0-9_]+\}")


@dataclass
class UnreviewedEntry:
    source: str  # "catalog" or "rules.yaml"
    lang: str
    key_or_code: str
    current_text: str
    reviewer: str = ""


@dataclass
class LinterReport:
    missing_keys: dict[str, set[str]] = field(default_factory=dict)
    placeholder_mismatches: list[str] = field(default_factory=list)
    rules_errors: list[str] = field(default_factory=list)
    unreviewed_entries: list[UnreviewedEntry] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        has_missing = any(bool(keys) for keys in self.missing_keys.values())
        return not has_missing and not self.placeholder_mismatches and not self.rules_errors


def extract_placeholders(text: str) -> set[str]:
    """Finds all format placeholders like {0}, {n} in a string."""
    return set(PLACEHOLDER_REGEX.findall(text))


def load_catalog(catalog_path: Path) -> dict[str, Any]:
    with open(catalog_path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)
        return data


def run_translation_checks(
    catalogs_dir: Path | str,
    rules_path: Path | str,
    project_root: Path | str | None = None,
) -> LinterReport:
    catalogs_path = Path(catalogs_dir)
    rules_file = Path(rules_path)
    root = Path(project_root) if project_root else rules_file.parent.parent

    report = LinterReport()

    # 1. Load catalogs
    loaded_catalogs: dict[str, dict[str, Any]] = {}
    for lang in SUPPORTED_LANGUAGES:
        c_path = catalogs_path / f"{lang}.json"
        if not c_path.exists():
            report.rules_errors.append(f"Catalog file missing: {c_path}")
            continue
        loaded_catalogs[lang] = load_catalog(c_path)

    # 2. Key Parity Check
    all_keys: set[str] = set()
    for cat in loaded_catalogs.values():
        all_keys.update(cat.keys())

    for lang in SUPPORTED_LANGUAGES:
        cat_keys = set(loaded_catalogs.get(lang, {}).keys())
        diff = all_keys - cat_keys
        if diff:
            report.missing_keys[lang] = diff

    # 3. Placeholder & Unreviewed checks in Catalogs
    for key in sorted(all_keys):
        expected_placeholders: set[str] | None = None
        for lang in SUPPORTED_LANGUAGES:
            entry = loaded_catalogs.get(lang, {}).get(key)
            if entry is None:
                continue

            # Extract text & placeholders
            texts_to_check: list[str] = []
            is_reviewed = False
            reviewer = ""

            if isinstance(entry, dict):
                is_reviewed = bool(entry.get("reviewed", False))
                reviewer = str(entry.get("reviewer", ""))
                # Could be standard text or plural form
                if "text" in entry:
                    texts_to_check.append(str(entry["text"]))
                for cat in ("other", "one", "few", "many"):
                    if cat in entry:
                        texts_to_check.append(str(entry[cat]))
            else:
                texts_to_check.append(str(entry))

            if not is_reviewed:
                sample_text = texts_to_check[0] if texts_to_check else ""
                report.unreviewed_entries.append(
                    UnreviewedEntry(
                        source=f"catalog:{lang}",
                        lang=lang,
                        key_or_code=key,
                        current_text=sample_text,
                        reviewer=reviewer,
                    )
                )

            # Check placeholders across texts for this key
            for txt in texts_to_check:
                ph = extract_placeholders(txt)
                if expected_placeholders is None:
                    expected_placeholders = ph
                elif ph != expected_placeholders:
                    report.placeholder_mismatches.append(
                        f"Key '{key}' in lang '{lang}' has placeholders {ph}, expected {expected_placeholders}"
                    )

    # 4. Rules YAML Verification
    if rules_file.exists():
        with open(rules_file, encoding="utf-8") as f:
            rules_raw = yaml.safe_load(f)

        rules_list = rules_raw.get("rules", [])
        for r in rules_list:
            code = r.get("code", "UNKNOWN")
            translations = r.get("translations", {})
            if not translations:
                report.rules_errors.append(f"Rule '{code}' has no 'translations' section")
                continue

            for lang in SUPPORTED_LANGUAGES:
                if lang not in translations:
                    report.rules_errors.append(
                        f"Rule '{code}' is missing translation for '{lang}'"
                    )
                    continue

                t_data = translations[lang]
                for required_field in ("title", "screen_text", "voice_file", "voice_text"):
                    if not t_data.get(required_field):
                        report.rules_errors.append(
                            f"Rule '{code}' lang '{lang}' is missing field '{required_field}'"
                        )

                if not t_data.get("reviewed", False):
                    report.unreviewed_entries.append(
                        UnreviewedEntry(
                            source=f"rules.yaml:{code}",
                            lang=lang,
                            key_or_code=f"{code}.{lang}",
                            current_text=str(t_data.get("title", "")),
                            reviewer=str(t_data.get("reviewer", "")),
                        )
                    )
    else:
        report.rules_errors.append(f"rules.yaml not found at {rules_file}")

    # 5. Generate TRANSLATION_REVIEW.md
    generate_review_markdown(root / "TRANSLATION_REVIEW.md", report)

    return report


def generate_review_markdown(output_path: Path, report: LinterReport) -> None:
    """Generates TRANSLATION_REVIEW.md detailing reviewed/unreviewed strings."""
    lines = [
        "# Translation Quality & Review Audit",
        "",
        "> This document is automatically generated by `src.driving_eval.i18n.check_translations`.",
        "",
        "## Summary",
        f"- Total unreviewed strings: **{len(report.unreviewed_entries)}**",
        f"- Missing keys across catalogs: **{sum(len(v) for v in report.missing_keys.values())}**",
        f"- Placeholder mismatches: **{len(report.placeholder_mismatches)}**",
        f"- Rules definition errors: **{len(report.rules_errors)}**",
        "",
    ]

    if report.missing_keys:
        lines.append("## Missing Keys by Language")
        for lang, keys in report.missing_keys.items():
            lines.append(f"### {lang} ({len(keys)} missing)")
            for k in sorted(keys):
                lines.append(f"- `{k}`")
            lines.append("")

    if report.placeholder_mismatches:
        lines.append("## Placeholder Mismatches")
        for m in report.placeholder_mismatches:
            lines.append(f"- {m}")
        lines.append("")

    if report.rules_errors:
        lines.append("## Rules Translation Errors")
        for err in report.rules_errors:
            lines.append(f"- ❌ {err}")
        lines.append("")

    lines.append("## Unreviewed Strings Audit Table")
    if not report.unreviewed_entries:
        lines.append("✅ **All translation keys and rule texts are fully reviewed and approved.**")
    else:
        lines.extend([
            "| Source | Language | Key / Code | Current Text | Methodologist / Reviewer | Status |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |",
        ])
        for entry in report.unreviewed_entries:
            reviewer_str = entry.reviewer if entry.reviewer else "_UNASSIGNED_"
            clean_text = entry.current_text.replace("\n", " ").replace("|", "\\|")
            lines.append(
                f"| `{entry.source}` | `{entry.lang}` | `{entry.key_or_code}` | {clean_text} | {reviewer_str} | ⚠️ Pending Review |"
            )

    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Translation Linter & Review Generator")
    parser.add_argument(
        "--catalogs-dir",
        default="src/driving_eval/i18n/catalogs",
        help="Path to catalogs directory",
    )
    parser.add_argument(
        "--rules-path",
        default="config/rules.yaml",
        help="Path to rules.yaml file",
    )
    args = parser.parse_args()

    catalogs_dir = Path(args.catalogs_dir)
    rules_path = Path(args.rules_path)

    report = run_translation_checks(catalogs_dir, rules_path)

    print("=== Translation Quality Report ===")
    print(f"Catalogs Directory: {catalogs_dir.resolve()}")
    print(f"Rules Path:         {rules_path.resolve()}")
    print(f"Status:             {'PASS' if report.is_valid else 'FAIL'}")

    if report.missing_keys:
        print("\n[ERROR] Missing Keys:")
        for lang, keys in report.missing_keys.items():
            print(f"  {lang}: {len(keys)} missing -> {sorted(keys)}")

    if report.placeholder_mismatches:
        print("\n[ERROR] Placeholder Mismatches:")
        for err in report.placeholder_mismatches:
            print(f"  - {err}")

    if report.rules_errors:
        print("\n[ERROR] Rules Configuration Errors:")
        for err in report.rules_errors:
            print(f"  - {err}")

    if report.unreviewed_entries:
        print(f"\n[WARNING] {len(report.unreviewed_entries)} entries pending methodologist review.")
        print("Generated review checklist at TRANSLATION_REVIEW.md")
    else:
        print("\n[OK] 100% of translations and rules are reviewed and verified.")

    return 0 if report.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
