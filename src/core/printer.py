"""Simple table and JSON printing helpers (no third-party deps)."""

from __future__ import annotations

import json
from typing import Iterable, List, Mapping, Sequence


def _col_widths(headers: Sequence[str], rows: Iterable[Mapping[str, object]]) -> List[int]:
    widths = [len(h) for h in headers]
    for r in rows:
        for i, h in enumerate(headers):
            v = r.get(h, "")
            widths[i] = max(widths[i], len(str(v)))
    return widths


def render_table(headers: Sequence[str], rows: List[Mapping[str, object]]) -> str:
    """Return a plain-text table string."""
    widths = _col_widths(headers, rows)
    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    sep = "  ".join("-" * w for w in widths)
    body = []
    for r in rows:
        body.append("  ".join(str(r.get(h, "")).ljust(w) for h, w in zip(headers, widths)))
    return "\n".join([line, sep] + body)


def print_table_or_json(headers: Sequence[str], rows: List[Mapping[str, object]], as_json: bool) -> None:
    """Print either JSON array or a textual table."""
    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        print(render_table(headers, rows))
