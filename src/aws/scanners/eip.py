from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from ...core.types import ResourceRecord
from ...core.pricing import PriceCache, estimate_eip_monthly
from ...core.policy import apply_filters
from ..session import AwsContext


class EipScanner:
    name = "eip"

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _age_days(self, alloc_time: datetime | None) -> Optional[int]:
        if not isinstance(alloc_time, datetime):
            return None
        delta = self._now() - alloc_time
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
        # DescribeAddresses isn't paginated for typical usage
        resp = ctx.ec2.describe_addresses()
        addrs = resp.get("Addresses", []) or []

        out: List[ResourceRecord] = []
        for a in addrs:
            # Skip associated
            if a.get("AssociationId"):
                continue

            alloc_id = a.get("AllocationId")
            public_ip = a.get("PublicIp")
            rid = alloc_id or public_ip  # EC2-Classic had no AllocationId
            alloc_time: datetime | None = a.get("AllocationTime")
            age = self._age_days(alloc_time)

            # If age gate configured, apply when we know the time
            if older_than_days is not None and age is not None and age < int(older_than_days):
                continue

            tags_list = a.get("Tags", []) or []
            tags = {t.get("Key"): t.get("Value") for t in tags_list if t and "Key" in t}
            name = tags.get("Name")

            rr = ResourceRecord(
                type="eip",
                id=str(rid),
                region=ctx.region,
                account=ctx.account_label,
                name=name,
                created_at=alloc_time.isoformat() if isinstance(alloc_time, datetime) else None,
                age_days=age,
                reason="unassociated",
                tags=tags,
                delete_action=["ec2:ReleaseAddress"],
                attributes={
                    "public_ip": public_ip,
                },
            )
            out.append(rr)

        # Apply filters (tags/name)
        out = apply_filters(out, exclude_tags, protect_name_regex)

        # Cost estimate
        for r in out:
            r.est_monthly_cost = estimate_eip_monthly(r, price_cache)

        return out
