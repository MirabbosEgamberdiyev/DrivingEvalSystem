"""Audit script leakage and translation quality across uz-Latn, uz-Cyrl, and ru catalogs."""

import json
import re
from pathlib import Path

cyrillic_re = re.compile(r"[\u0400-\u04FF]")
uz_specific_cyrl = re.compile(r"[қғҳўҚҒҲЎ]")
latn_words_re = re.compile(r"\b[A-Za-z]{3,}\b")

# Whitelist of technical acronyms / uppercase codes allowed in Cyrillic
whitelist = {
    "FRONT", "REAR", "LEFT", "RIGHT", "OBD", "GPS", "FPS", "WAV", "ONNX",
    "DIRECTML", "VIN", "CAR", "USB", "PDF", "CSV", "JSON", "RAM", "CPU",
    "GB", "MB", "KB", "WMI", "IPM", "BEV", "ESTAKADA", "ZMEIKA", "PARALLEL",
    "GARAG", "STOP", "LINE", "CONE", "SEATBELT", "COLLISION", "SPEED",
    "HANDBRAKE", "SIGNAL", "LIGHTS", "REVERSING", "PEDESTRIAN", "HTML",
    "SHA", "ED25519", "HMAC", "NEXIA", "STANDALONE", "ONLINE", "OFFLINE",
    "CHECKING", "FAILED", "PASSED", "READY", "HOME", "TEST", "CIM", "API",
    "ISO", "UTC", "KMH", "RPM", "VOLT", "CUDA", "TENSORRT", "MICROSOFT",
    "WINDOWS", "PYSIDE", "PYTHON", "SQLITE", "ICU", "WCAG", "AAA", "HUD",
    "GNSS", "IMU", "CAN", "NVME", "SSD", "WAL", "PIN", "TTS"
}

def audit_catalogs():
    cat_dir = Path("src/driving_eval/i18n/catalogs")
    latn_data = json.loads((cat_dir / "uz-Latn.json").read_text(encoding="utf-8"))
    cyrl_data = json.loads((cat_dir / "uz-Cyrl.json").read_text(encoding="utf-8"))
    ru_data = json.loads((cat_dir / "ru.json").read_text(encoding="utf-8"))

    issues = []

    # 1. Check uz-Latn for Cyrillic letters
    for k, v in latn_data.items():
        t = v.get("text", "") if isinstance(v, dict) else str(v)
        m = cyrillic_re.findall(t)
        if m:
            issues.append(f"[uz-Latn Cyrillic leak] {k}: found {set(m)} in '{t}'")

    # 2. Check ru for Uzbek-specific Cyrillic or Uzbek apostrophe words
    for k, v in ru_data.items():
        t = v.get("text", "") if isinstance(v, dict) else str(v)
        m = uz_specific_cyrl.findall(t)
        if m:
            issues.append(f"[ru Uzbek-Cyrillic leak] {k}: found {set(m)} in '{t}'")
        if "o'" in t.lower() or "g'" in t.lower() or "o‘" in t.lower() or "g‘" in t.lower():
            issues.append(f"[ru Uzbek-Latin leak] {k}: found Uzbek apostrophe in '{t}'")

    # 3. Check uz-Cyrl for Latin words not in whitelist
    for k, v in cyrl_data.items():
        t = v.get("text", "") if isinstance(v, dict) else str(v)
        words = latn_words_re.findall(t)
        leaks = [w for w in words if w.upper() not in whitelist]
        if leaks:
            issues.append(f"[uz-Cyrl Latin leak] {k}: found {leaks} in '{t}'")

    print(f"Total script leakage issues found: {len(issues)}")
    for iss in issues:
        print("  -", iss)
    return len(issues)

if __name__ == "__main__":
    import sys
    if sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(audit_catalogs())
