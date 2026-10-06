"""Structured logging configuration for offline driving evaluation system.

Provides formatted console and rotating JSON file logs.
No external network telemetry or third-party log forwarding.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path


class JsonLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        # Any extra fields passed via extra={}
        if hasattr(record, "session_id"):
            log_obj["session_id"] = record.session_id
        if hasattr(record, "state"):
            log_obj["state"] = record.state
        if hasattr(record, "car_id"):
            log_obj["car_id"] = record.car_id

        return json.dumps(log_obj, ensure_ascii=False)


def setup_logging(
    log_file_path: str | Path = "data/logs/system.log",
    level: str = "INFO",
    console_output: bool = True,
) -> logging.Logger:
    """Configures system-wide logger with both readable console and JSON file outputs."""
    logger = logging.getLogger("driving_eval")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    # Clear existing handlers to avoid duplicates
    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler (Human-readable)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_fmt = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_fmt)
        logger.addHandler(console_handler)

    # File Handler (JSON structured)
    p = Path(log_file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(p, encoding="utf-8")
    file_handler.setFormatter(JsonLogFormatter())
    logger.addHandler(file_handler)

    return logger
