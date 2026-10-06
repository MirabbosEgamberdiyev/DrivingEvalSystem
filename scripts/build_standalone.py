"""Standalone Windows Build Script using Nuitka / PyInstaller for Driving Evaluation System.

Prepares standalone binary distribution in dist/driving_eval/ with all offline assets,
QML schemas, 3-language audio WAVs, ONNX models, and config templates.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("build_standalone")


def assemble_distribution_tree(target_dir: Path, source_root: Path) -> None:
    """Assembles all required offline data files, configs, and assets into target distribution folder."""
    target_dir.mkdir(parents=True, exist_ok=True)

    assets_to_copy = [
        ("config", target_dir / "config"),
        ("data/audio", target_dir / "data" / "audio"),
        ("data/models", target_dir / "data" / "models"),
        ("src/driving_eval/ui_qml/qml", target_dir / "driving_eval" / "ui_qml" / "qml"),
        ("src/driving_eval/i18n/catalogs", target_dir / "driving_eval" / "i18n" / "catalogs"),
    ]

    for src_rel, dst in assets_to_copy:
        src = source_root / src_rel
        if src.exists():
            if src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                logger.info("Copied asset tree: %s -> %s", src_rel, dst)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                logger.info("Copied asset file: %s -> %s", src_rel, dst)
        else:
            logger.warning("Source asset not found: %s", src)


def run_nuitka_compilation(source_root: Path, output_dir: Path) -> bool:
    """Executes Nuitka standalone compilation targeting Windows x64."""
    entry_script = source_root / "src" / "driving_eval" / "ui_qml" / "app.py"

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyside6",
        "--windows-console-mode=disable",
        f"--output-dir={output_dir}",
        "--output-filename=driving_eval.exe",
        str(entry_script),
    ]

    logger.info("Executing Nuitka build: %s", " ".join(cmd))
    try:
        ret = subprocess.run(cmd, check=True)
        return ret.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error("Nuitka build failed or Nuitka not installed: %s", e)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Standalone Windows packager for Driving Evaluation System")
    parser.add_argument("--dry-run", action="store_true", help="Assemble distribution directory without compilation")
    parser.add_argument("--out", default="dist/driving_eval", help="Output distribution folder")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / args.out

    logger.info("Starting standalone build preparation...")
    assemble_distribution_tree(dist_dir, project_root)

    if args.dry_run:
        logger.info("[DRY-RUN] Distribution tree prepared successfully at: %s", dist_dir)
        return 0

    success = run_nuitka_compilation(project_root, dist_dir.parent)
    if success:
        logger.info("Compilation completed successfully.")
        return 0
    else:
        logger.warning("Nuitka compilation bypassed or failed. Tree is assembled in %s", dist_dir)
        return 1


if __name__ == "__main__":
    sys.exit(main())
