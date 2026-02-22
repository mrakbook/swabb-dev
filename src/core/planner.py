from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, List

from .. import __version__
from .types import ResourceRecord


def records_to_json(records: List[ResourceRecord]) -> List[Dict]:
    out: List[Dict] = []
    for r in records:
        out.append(
            {
                "type": r.type,
                "id": r.id,
                "region": r.region,
                "account": r.account,
                "name": r.name,
                "created_at": r.created_at,
                "age_days": r.age_days,
                "reason": r.reason,
                "tags": r.tags,
                "est_monthly_cost": r.est_monthly_cost,
                "delete_action": r.delete_action,
                "attributes": r.attributes,
            }
        )
    return out


def build_plan(records: List[ResourceRecord], policy: Dict) -> Dict:
    total_cost = sum([r.est_monthly_cost or 0.0 for r in records])
    plan = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "swabb_version": __version__,
        "policy": policy,
        "resources": records_to_json(records),
        "totals": {
            "count": len(records),
            "est_monthly_savings": round(total_cost, 2),
        },
    }
    return plan


def dump_plan(path: str, plan: Dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
