from __future__ import annotations

from typing import List, Mapping, Sequence, Tuple

from .types import ResourceRecord
from .printer import print_table_or_json


def _fmt_cost(v) -> str:
    if v is None:
        return "-"
    return f"{v:.2f}"


def rows_for_table(records: List[ResourceRecord]) -> Tuple[Sequence[str], List[Mapping[str, object]]]:
    headers = ["Type", "ID", "Region", "Age(d)", "Size(GB)", "$/Month", "Reason"]
    rows: List[Mapping[str, object]] = []
    for r in records:
        size = "-"  # default
        if r.type == "ebs":
            size = r.attributes.get("size_gb", "-")
        rows.append(
            {
                "Type": r.type,
                "ID": r.id,
                "Region": r.region,
                "Age(d)": r.age_days if r.age_days is not None else "-",
                "Size(GB)": size,
                "$/Month": _fmt_cost(r.est_monthly_cost),
                "Reason": r.reason or "",
            }
        )
    return headers, rows


def print_report(records: List[ResourceRecord], as_json: bool) -> None:
    headers, rows = rows_for_table(records)
    print_table_or_json(headers, rows, as_json=as_json)
