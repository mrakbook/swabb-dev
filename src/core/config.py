"""Configuration loader + account/region resolver for swabb (M1)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

# Optional YAML support (only if PyYAML is installed)
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    yaml = None  # type: ignore


# A pragmatic, static list; expand later as needed.
DEFAULT_AWS_REGIONS: List[str] = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ca-central-1",
    "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-central-1", "eu-central-2",
    "eu-north-1", "eu-south-1", "eu-south-2",
    "ap-south-1", "ap-south-2",
    "ap-southeast-1", "ap-southeast-2", "ap-southeast-3",
    "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "ap-east-1",
    "me-south-1", "me-central-1",
    "sa-east-1",
    "af-south-1",
]


@dataclass
class Account:
    profile: Optional[str] = None
    role_arn: Optional[str] = None
    regions: Union[str, List[str]] = "all"

    def label(self) -> str:
        return self.profile or (self.role_arn or "default")


@dataclass
class CostConfig:
    enabled: bool = True
    pricing_cache_ttl_hours: int = 24
    fallback_estimates: Dict[str, float] = field(default_factory=dict)


@dataclass
class SwabbConfig:
    accounts: List[Account] = field(default_factory=lambda: [Account(profile="default", regions="all")])
    thresholds: Dict[str, int] = field(default_factory=lambda: {"ebs_idle_days": 30, "eip_idle_days": 0})
    exclude_tags: List[str] = field(default_factory=list)
    protect_name_regex: Optional[str] = None
    cost: CostConfig = field(default_factory=CostConfig)


_DEFAULT_SEARCH = [
    "./swabb.yml",
    "./swabb.yaml",
    "./swabb.json",
    os.path.join(Path.home(), ".swabb", "config.yml"),
    os.path.join(Path.home(), ".swabb", "config.json"),
]


def _load_yaml(path: str) -> Dict:
    if not yaml:
        raise RuntimeError("YAML config requested but PyYAML is not installed. Install with: pip install 'swabb[yaml]'")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config(path_hint: Optional[str] = None) -> SwabbConfig:
    """Load YAML/JSON config or fall back to sensible defaults."""
    path = None
    candidates = [path_hint] if path_hint else _DEFAULT_SEARCH
    for c in candidates:
        if c and os.path.isfile(c):
            path = c
            break

    if not path:
        return SwabbConfig()

    try:
        if path.endswith((".yml", ".yaml")):
            data = _load_yaml(path)
        else:
            data = _load_json(path)
    except Exception as e:
        raise RuntimeError(f"Failed to read config {path}: {e}") from e

    accounts: List[Account] = []
    for raw in data.get("accounts", []):
        accounts.append(
            Account(
                profile=raw.get("profile"),
                role_arn=raw.get("role_arn"),
                regions=raw.get("regions", "all"),
            )
        )

    # cost config
    c = data.get("cost", {}) or {}
    cost = CostConfig(
        enabled=bool(c.get("enabled", True)),
        pricing_cache_ttl_hours=int(c.get("pricing_cache_ttl_hours", 24)),
        fallback_estimates=dict(c.get("fallback_estimates", {})),
    )

    return SwabbConfig(
        accounts=accounts or [Account(profile="default", regions="all")],
        thresholds=data.get("thresholds", {"ebs_idle_days": 30, "eip_idle_days": 0}),
        exclude_tags=list(data.get("exclude_tags", [])),
        protect_name_regex=data.get("protect_name_regex"),
        cost=cost,
    )


def resolve_regions(regions_opt: Optional[str], cfg: SwabbConfig) -> List[Tuple[Account, str]]:
    """
    Determine list of (Account, region) tuples to iterate.

    - If regions_opt is provided, apply to the *first* account only (M1 simplicity).
    - Otherwise, respect each account's configured regions (list or "all").
    """
    pairs: List[Tuple[Account, str]] = []
    if regions_opt:
        acct = cfg.accounts[0] if cfg.accounts else Account(profile="default", regions="all")
        regions = DEFAULT_AWS_REGIONS if regions_opt == "all" else [r.strip() for r in regions_opt.split(",") if r.strip()]
        for r in regions:
            pairs.append((acct, r))
        return pairs

    for acct in cfg.accounts or [Account(profile="default", regions="all")]:
        if acct.regions == "all":
            regs = DEFAULT_AWS_REGIONS
        elif isinstance(acct.regions, list):
            regs = acct.regions
        else:
            regs = DEFAULT_AWS_REGIONS
        for r in regs:
            pairs.append((acct, r))
    return pairs
