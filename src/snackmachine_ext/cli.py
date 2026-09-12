"""CLI for SnackMachine extension."""
from __future__ import annotations

import argparse
import json
import platform
import sys

from .activity_capture import ActivityCaptureEngine
from .action_runner import default_runner
from .launcher import discover_launchers
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


def cmd_launchers(all_items: bool = False) -> int:
    launchers = discover_launchers(include_absent=all_items)
    print(json.dumps({
        "launchers": launchers,
        "count": len(launchers),
        "absent_hidden": not all_items,
    }, indent=2))
    return 0


def cmd_capture(sources: list[str] | None = None) -> int:
    engine = ActivityCaptureEngine()
    result = engine.run_sync(sources=sources)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def cmd_actions() -> int:
    actions = default_runner.list_actions()
    print(json.dumps({"actions": actions, "count": len(actions)}, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="SnackMachine extension CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("doctor", help="Show local extension health info")
    sub.add_parser("capabilities", help="Print uCore capability manifest")

    p_launchers = sub.add_parser("launchers", help="List discovered product launchers (absent hidden)")
    p_launchers.add_argument("--all", action="store_true", help="Include absent products")

    p_capture = sub.add_parser("capture", help="Perform bounded Apple activity capture")
    p_capture.add_argument("--source", action="append", dest="sources", help="Specific sources (calendar, reminders, notes, mail)")

    sub.add_parser("actions", help="List available snack actions")

    args = parser.parse_args()

    if args.command == "doctor":
        raise SystemExit(cmd_doctor())
    if args.command == "capabilities":
        raise SystemExit(cmd_capabilities())
    if args.command == "launchers":
        raise SystemExit(cmd_launchers(all_items=args.all))
    if args.command == "capture":
        raise SystemExit(cmd_capture(sources=args.sources))
    if args.command == "actions":
        raise SystemExit(cmd_actions())

    parser.print_help()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
