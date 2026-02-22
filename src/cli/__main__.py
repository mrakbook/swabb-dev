#!/usr/bin/env python3
"""
swabb CLI single entrypoint.

- `python -m src.cli`
- Console script: `swabb` (via pyproject)
"""

from __future__ import annotations

import argparse
import logging

from ._shared import DISPLAY_VERSION, set_console_log_level
from .help import CLI_DESCRIPTION
from .commands.scan import register_scan_command


def main() -> None:
    parser = argparse.ArgumentParser(prog="swabb", description=CLI_DESCRIPTION)
    parser.add_argument("-V", "--version", action="version", version=f"swabb {DISPLAY_VERSION}")
    parser.add_argument("--json", action="store_true", help="(Reserved) Output results as JSON when applicable")

    subparsers = parser.add_subparsers(dest="command", required=True)

    register_scan_command(subparsers)

    args = parser.parse_args()

    set_console_log_level(logging.INFO)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
