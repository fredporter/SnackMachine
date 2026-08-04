"""CLI for SnackMachine extension."""
from __future__ import annotations

import argparse
import json
import platform
import sys

from .manifest import capability_manifest


def cmd_doctor() -> int:
    info = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "extension": "snackmachine-extension",
        "status": "ok",
    }
    print(json.dumps(info, indent=2))
    return 0


def cmd_capabilities() -> int:
    print(json.dumps(capability_manifest(), indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="SnackMachine extension CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("doctor", help="Show local extension health info")
    sub.add_parser("capabilities", help="Print uCore capability manifest")

    args = parser.parse_args()

    if args.command == "doctor":
        raise SystemExit(cmd_doctor())
    if args.command == "capabilities":
        raise SystemExit(cmd_capabilities())

    parser.print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
