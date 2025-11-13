"""Configuration loader + region resolver for swabb (M0; no AWS calls)."""

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


# A pragmatic, static list for M0. You can expand later.
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


@dataclass
class SwabbConfig:
    accounts: List[Account] = field(default_factory=lambda: [Account(profile="default", regions="all")])
    thresholds: Dict[str, int] = field(default_factory=lambda: {"ebs_idle_days": 30})
    exclude_tags: List[str] = field(default_factory=list)
    protect_name_regex: Optional[str] = None


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

    accounts = []
    for raw in data.get("accounts", []):
        accounts.append(
            Account(
                profile=raw.get("profile"),
                role_arn=raw.get("role_arn"),
                regions=raw.get("regions", "all"),
            )
        )

    return SwabbConfig(
        accounts=accounts or [Account(profile="default", regions="all")],
        thresholds=data.get("thresholds", {"ebs_idle_days": 30}),
        exclude_tags=list(data.get("exclude_tags", [])),
        protect_name_regex=data.get("protect_name_regex"),
    )


def resolve_regions(regions_opt: Optional[str], cfg: SwabbConfig) -> List[Tuple[str, str]]:
    """
    Determine (account_label, region) tuples to iterate.
    - regions_opt: CLI comma list or "all". If given, applies to the first/only account.
    - otherwise use each account's regions config (list or "all").
    """
    pairs: List[Tuple[str, str]] = []
    if regions_opt:
        # Apply to first account only for M0
        acct = cfg.accounts[0] if cfg.accounts else Account(profile="default", regions="all")
        label = acct.profile or (acct.role_arn or "default")
        regions = DEFAULT_AWS_REGIONS if regions_opt == "all" else [r.strip() for r in regions_opt.split(",") if r.strip()]
        for r in regions:
            pairs.append((label, r))
        return pairs

    # From config
    accts = cfg.accounts or [Account(profile="default", regions="all")]
    for acct in accts:
        label = acct.profile or (acct.role_arn or "default")
        if acct.regions == "all":
            regs = DEFAULT_AWS_REGIONS
        elif isinstance(acct.regions, list):
            regs = acct.regions
        else:
            regs = DEFAULT_AWS_REGIONS
        for r in regs:
            pairs.append((label, r))
    return pairs
