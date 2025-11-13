"""`swabb scan` command (Milestone 1: AWS EBS/EIP scan + plan + pretty table)."""

from __future__ import annotations

import argparse
import logging
import time
from typing import Dict, List

from ...core.config import Account, SwabbConfig, load_config, resolve_regions
from ...core.logging import audit_event, init_audit_logger
from ...core.planner import build_plan, dump_plan
from ...core.pricing import PriceCache
from ...core.reporter import print_report
from ...core.types import ResourceRecord
from ...aws.registry import get as get_scanner, list_supported
from ...aws.session import build_ctx


def register_scan_command(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "scan",
        help="Scan (dry-run): find unattached EBS volumes & unassociated EIPs; print table/JSON plan",
    )
    p.add_argument("--config", help="Path to YAML/JSON config file (default search paths apply)")
    p.add_argument(
        "--regions",
        help='Comma-separated region list or "all". Overrides config for first account (M1).',
    )
    p.add_argument(
        "-t",
        "--resource-types",
        default="ebs,eip",
        help="Comma-separated resource types to scan (supported: ebs,eip; default: ebs,eip)",
    )
    p.add_argument(
        "--older-than",
        type=int,
        default=None,
        help="Global age threshold in days (overrides resource-specific thresholds in config)",
    )
    p.add_argument(
        "--cost",
        action="store_true",
        default=False,
        help="Estimate monthly cost using pricing cache + config fallback",
    )
    p.add_argument(
        "-o",
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    p.add_argument("--plan-out", help="Write the JSON plan to this file")
    p.add_argument("-q", "--quiet", action="store_true", default=False, help="Minimal console logs (ERROR only)")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose console logs (INFO)")
    p.add_argument("--debug", action="store_true", help="Debug console logs (DEBUG)")
    p.set_defaults(func=_handle_scan)


def _resolve_threshold(rt: str, global_days: int | None, cfg: SwabbConfig) -> int | None:
    if global_days is not None:
        return global_days
    # Use type-specific thresholds if present
    if rt == "ebs":
        return int(cfg.thresholds.get("ebs_idle_days", 30))
    if rt == "eip":
        # Default 0 meaning "don't gate by age unless known and explicitly configured"
        return int(cfg.thresholds.get("eip_idle_days", 0))
    return None


def _scan_one_region(acct: Account, region: str, rtypes: List[str], cfg: SwabbConfig, price_cache: PriceCache) -> List[ResourceRecord]:
    results: List[ResourceRecord] = []
    ctx = build_ctx(region=region, profile=acct.profile, account_label=acct.label())

    for rt in rtypes:
        scanner = get_scanner(rt)
        threshold = _resolve_threshold(rt, global_days=None, cfg=cfg)
        # Use the global --older-than only once per call chain
        out = scanner.scan(
            ctx=ctx,
            older_than_days=threshold,
            exclude_tags=cfg.exclude_tags,
            protect_name_regex=cfg.protect_name_regex,
            price_cache=price_cache,
            thresholds=cfg.thresholds,
        )
        results.extend(out)
    return results


def perform_scan(cfg: SwabbConfig, regions_opt: str | None, rtypes_csv: str, cost_flag: bool) -> List[ResourceRecord]:
    # Price cache
    price_cache = PriceCache(
        enabled=bool(cfg.cost.enabled and cost_flag),
        ttl_hours=int(cfg.cost.pricing_cache_ttl_hours),
        fallback=dict(cfg.cost.fallback_estimates or {}),
    )

    pairs = resolve_regions(regions_opt, cfg)

    all_records: List[ResourceRecord] = []
    for acct, region in pairs:
        recs = _scan_one_region(acct, region, [rt.strip() for rt in rtypes_csv.split(",") if rt.strip()], cfg, price_cache)
        all_records.extend(recs)
    return all_records


def _handle_scan(args) -> None:
    # Decide file/console log levels
    file_level = logging.DEBUG if args.debug else logging.INFO
    if args.quiet:
        console_level = logging.ERROR
    elif args.debug:
        console_level = logging.DEBUG
    elif args.verbose:
        console_level = logging.INFO
    else:
        console_level = logging.WARNING

    logger = init_audit_logger(file_level=file_level, console_level=console_level)

    # Load config
    try:
        cfg: SwabbConfig = load_config(args.config)
    except Exception as e:
        print(f"Config error: {e}")
        return

    # Validate resource types
    req_types = [t.strip() for t in args.resource_types.split(",") if t.strip()]
    for t in req_types:
        if t not in list_supported():
            print(f"Unsupported resource type: {t}. Supported: {', '.join(list_supported())}")
            return

    audit_event(logger, "scan.start", accounts=len(cfg.accounts), requested_types=req_types)
    start = time.time()

    # Build records (scan)
    records = perform_scan(cfg, args.regions, args.resource_types, args.cost)

    # If a global --older-than was provided, re-apply (overriding per-type)
    if args.older_than is not None:
        records = [r for r in records if r.age_days is None or r.age_days >= int(args.older_than)]
        for r in records:
            if r.type == "ebs":
                r.reason = f"unattached ≥ {args.older_than} days"
            elif r.type == "eip":
                r.reason = f"unassociated (age ≥ {args.older_than} days)" if r.age_days is not None else "unassociated"

    dur = round((time.time() - start) * 1000)
    audit_event(logger, "scan.done", duration_ms=dur, regions_scanned=len(set([r.region for r in records])))

    # Emit plan
    policy = {
        "thresholds": cfg.thresholds,
        "exclude_tags": cfg.exclude_tags,
        "protect_name_regex": cfg.protect_name_regex,
        "cost_enabled": bool(cfg.cost.enabled and args.cost),
    }
    plan = build_plan(records, policy)

    # Write plan-out if requested
    if args.plan_out:
        dump_plan(args.plan_out, plan)

    # Print report
    if args.output == "json":
        # print the plan resources & totals (human-friendly plan view)
        from .._shared import print_or_json
        print_or_json(plan, as_json=True)
    else:
        print_report(records, as_json=False)
