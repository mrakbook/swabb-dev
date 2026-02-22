from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from ...core.types import ResourceRecord
from ...core.pricing import PriceCache, estimate_ebs_monthly
from ...core.policy import apply_filters
from ..session import AwsContext


class EbsScanner:
    name = "ebs"

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _age_days(self, created: datetime) -> int:
        delta = self._now() - created
        return max(int(delta.total_seconds() // 86400), 0)

    def scan(
        self,
        ctx: AwsContext,
        older_than_days: Optional[int],
        exclude_tags: List[str],
        protect_name_regex: Optional[str],
        price_cache: PriceCache,
        thresholds: Dict[str, int],
    ) -> List[ResourceRecord]:
        # Server-side filter by status
        resp = ctx.ec2.describe_volumes(Filters=[{"Name": "status", "Values": ["available"]}])
        vols = resp.get("Volumes", []) or []

        out: List[ResourceRecord] = []
        for v in vols:
            vol_id = v["VolumeId"]
            created: datetime = v.get("CreateTime")  # tz-aware
            age = self._age_days(created) if isinstance(created, datetime) else None
            if older_than_days is not None and age is not None and age < int(older_than_days):
                continue

            tags_list = v.get("Tags", []) or []
            tags = {t.get("Key"): t.get("Value") for t in tags_list if t and "Key" in t}
            name = tags.get("Name")

            rr = ResourceRecord(
                type="ebs",
                id=vol_id,
                region=ctx.region,
                account=ctx.account_label,
                name=name,
                created_at=created.isoformat() if isinstance(created, datetime) else None,
                age_days=age,
                reason=f"unattached ≥ {older_than_days} days" if older_than_days else "unattached",
                tags=tags,
                delete_action=["ec2:DeleteVolume"],
                attributes={
                    "size_gb": v.get("Size"),
                    "volume_type": v.get("VolumeType"),
                    "iops": v.get("Iops"),
                    "throughput": v.get("Throughput"),
                },
            )

            out.append(rr)

        # Tag/name-based filters
        out = apply_filters(out, exclude_tags, protect_name_regex)

        # Cost estimation (stub/cache/fallback)
        for r in out:
            r.est_monthly_cost = estimate_ebs_monthly(r, price_cache)

        return out
