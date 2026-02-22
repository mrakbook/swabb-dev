"""Audit logging utilities for swabb."""

from __future__ import annotations

import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


_LOGGER_NAME = "swabb"
_DEFAULT_DIR = os.path.join(Path.home(), ".swabb", "logs")
_DEFAULT_FILE = os.path.join(_DEFAULT_DIR, "swabb.log")


def init_audit_logger(
    file_level: int = logging.INFO,
    console_level: int = logging.WARNING,
    logfile: Optional[str] = None,
) -> logging.Logger:
    """
    Create (or reconfigure) a logger with:
      - Rotating file handler at ~/.swabb/logs/swabb.log (JSON-friendly format)
      - Console handler (human-friendly; level controlled by console_level)

    Safe to call multiple times; subsequent calls update handler levels.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG)  # capture everything; handlers filter

    os.makedirs(_DEFAULT_DIR, exist_ok=True)
    path = logfile or _DEFAULT_FILE

    # If already initialized, just tweak handler levels and return.
    if getattr(logger, "_initialized", False):
        for h in logger.handlers:
            try:
                if isinstance(h, RotatingFileHandler):
                    h.setLevel(file_level)
                elif isinstance(h, logging.StreamHandler):
                    h.setLevel(console_level)
            except Exception:
                pass
        return logger

    # File (rotating) handler
    fh = RotatingFileHandler(path, maxBytes=2 * 1024 * 1024, backupCount=3)
    fh.setLevel(file_level)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))

    # Console handler (quiet by default; show only WARNING+)
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(logging.Formatter("%(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)

    setattr(logger, "_initialized", True)
    return logger


def audit_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    """
    Write a structured JSON line to the file handler at INFO level, e.g.:
      {"event": "scan.region.start", "region": "us-east-1"}

    Console remains human-friendly via the console handler; level is configurable.
    """
    try:
        payload: Dict[str, Any] = {"event": event}
        payload.update(fields)
        logger.info(json.dumps(payload, ensure_ascii=False))
    except Exception:
        # Never fail the CLI due to logging; print minimal info
        logger.info({"event": event, **fields})
