"""`swabb scan` command (Milestone 0: no AWS calls, just config + region iteration)."""

from __future__ import annotations

import argparse
import logging
import time
from typing import Dict, List

from ...core.config import SwabbConfig, load_config, resolve_regions
from ...core.logging import audit_event, init_audit_logger
from ...core.printer import print_table_or_json
from .._shared import print_or_json


def register_scan_command(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "scan",
        help="Scan (dry-run): iterate configured regions (no AWS calls yet)",
    )
    p.add_argument("--config", help="Path to YAML/JSON config file (default search paths apply)")
    p.add_argument(
        "--regions",
        help='Comma-separated region list or "all". Overrides config for M0 (first account).',
    )
    p.add_argument(
        "-o",
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    # FIX: argparse boolean flag must use store_true/store_false, not action='bool'
    p.add_argument("-q", "--quiet", action="store_true", default=False, help="Minimal console logs (ERROR only)")
    p.add_argument("-v", "--verbose", action="store_true", help="Verbose console logs (INFO)")
    p.add_argument("--debug", action="store_true", help="Debug console logs (DEBUG)")
    p.set_defaults(func=_handle_scan)


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
        # Quiet-by-default console so audit JSON doesn't clutter stdout tables
        console_level = logging.WARNING

    logger = init_audit_logger(file_level=file_level, console_level=console_level)

    # Load config
    try:
        cfg: SwabbConfig = load_config(args.config)
    except Exception as e:
        print(f"Config error: {e}")
        return

    pairs = resolve_regions(args.regions, cfg)

    audit_event(logger, "scan.start", accounts=len(cfg.accounts), regions=len(pairs))
    start = time.time()

    # M0: no AWS calls; simulate per-region scan stub.
    rows: List[Dict[str, object]] = []
    for acct_label, region in pairs:
        audit_event(logger, "scan.region.start", account=acct_label, region=region)
        note = "stub (no AWS calls)"
        rows.append({"Account": acct_label, "Region": region, "Status": "ok", "Note": note})
        audit_event(logger, "scan.region.done", account=acct_label, region=region, ok=True)

    dur = round((time.time() - start) * 1000)
    audit_event(logger, "scan.done", duration_ms=dur, regions=len(rows))

    if args.output == "json":
        print_or_json(
            {
                "ok": True,
                "regions": [
                    {"account": r["Account"], "region": r["Region"], "status": r["Status"], "note": r["Note"]}
                    for r in rows
                ],
                "duration_ms": dur,
            },
            as_json=True,
        )
    else:
        headers = ["Account", "Region", "Status", "Note"]
        print_table_or_json(headers, rows, as_json=False)
