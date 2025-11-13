from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

from .types import ResourceRecord


@dataclass
class PriceCache:
    enabled: bool
    ttl_hours: int
    fallback: Dict[str, float]
    cache_file: str = os.path.join(Path.home(), ".swabb", "cache", "pricing.json")

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _load_cached(self) -> Dict[str, float]:
        try:
            if not os.path.isfile(self.cache_file):
                return {}
            stat = os.stat(self.cache_file)
            mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            if self._now() - mtime > timedelta(hours=self.ttl_hours):
                return {}
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception:
            return {}

    def _save_cached(self, data: Dict[str, float]) -> None:
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def get(self, key: str) -> Optional[float]:
        if not self.enabled:
            return None
        data = self._load_cached()
        if key in data:
            return data[key]
        # No real Pricing API calls in M1; rely on fallback (and persist it)
        if key in self.fallback:
            data[key] = self.fallback[key]
            self._save_cached(data)
            return data[key]
        return None


def _fmt_region(region: str) -> str:
    return region or "us-east-1"


def estimate_ebs_monthly(rr: ResourceRecord, cache: PriceCache) -> Optional[float]:
    region = _fmt_region(rr.region)
    vol_type = (rr.attributes.get("volume_type") or "gp3").lower()
    size_gb = int(rr.attributes.get("size_gb") or 0)
    key_specific = f"ebs_{vol_type}_gb_month_{region}"
    key_default = f"ebs_gp3_gb_month_{region}"
    price_per_gb = cache.get(key_specific) or cache.get(key_default)
    if price_per_gb is None:
        # Final fallback: a conservative default if user provided none (gp3/us-east-1 0.08)
        price_per_gb = cache.fallback.get("ebs_gp3_gb_month_us-east-1", 0.08)
    return round(float(size_gb) * float(price_per_gb), 2)


def estimate_eip_monthly(rr: ResourceRecord, cache: PriceCache) -> Optional[float]:
    region = _fmt_region(rr.region)
    key = f"eip_month_{region}"
    p = cache.get(key)
    if p is None:
        p = cache.fallback.get("eip_month_us-east-1", 3.60)
    return round(float(p), 2)
