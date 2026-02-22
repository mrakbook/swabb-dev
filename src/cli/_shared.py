"""Shared CLI utilities: version banner, JSON printer, logger bootstrap."""

from __future__ import annotations

import json
import logging
from typing import Any

from .. import __version__ as BASE_VERSION

# Allow a build script to inject an EFFECTIVE_VERSION via src/_build_meta.py,
# mirroring the pattern used in whyx packaging. If not present, fall back.
try:
    from .. import _build_meta as _bm  # type: ignore

    DISPLAY_VERSION = getattr(_bm, "EFFECTIVE_VERSION", BASE_VERSION) or BASE_VERSION
except Exception:
    DISPLAY_VERSION = BASE_VERSION


def print_or_json(obj: Any, as_json: bool) -> None:
    """Print JSON when --json is set; otherwise a human-friendly string/JSON."""
    if as_json:
        print(json.dumps(obj, indent=2))
    else:
        if isinstance(obj, (dict, list)):
            print(json.dumps(obj, indent=2))
        else:
            print(obj)


def set_console_log_level(level: int) -> None:
    """Adjust root console handler level in addition to audit file logging."""
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, logging.StreamHandler):
            h.setLevel(level)
