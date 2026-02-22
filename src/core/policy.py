from __future__ import annotations

import re
from typing import Dict, Iterable, List

from .types import ResourceRecord


def _parse_exclude_token(tok: str) -> tuple[str, str | None]:
    if "=" in tok:
        k, v = tok.split("=", 1)
        return k.strip(), v.strip()
    return tok.strip(), None


def should_exclude(tags: Dict[str, str], name: str | None, exclude_tags: List[str], protect_name_regex: str | None) -> bool:
    # Tag-based exclusion
    for tok in exclude_tags or []:
        k, v = _parse_exclude_token(tok)
        if k in tags:
            if v is None or str(tags.get(k)) == v:
                return True

    # Name-based protection
    if protect_name_regex and name:
        try:
            if re.search(protect_name_regex, name):
                return True
        except re.error:
            # invalid regex → ignore silently for now
            pass
    return False


def apply_filters(records: Iterable[ResourceRecord], exclude_tags: List[str], protect_name_regex: str | None) -> List[ResourceRecord]:
    out: List[ResourceRecord] = []
    for r in records:
        if should_exclude(r.tags or {}, r.name, exclude_tags, protect_name_regex):
            continue
        out.append(r)
    return out
