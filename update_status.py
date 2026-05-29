#!/usr/bin/env python3
"""Update the current status and automatically archive the previous one to history."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

VALID_STATUSES = ["operational", "maintenance", "degraded", "outage"]

def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def main():
    parser = argparse.ArgumentParser(
        description="Update login node status and regenerate the page.",
        epilog="""Examples:
  %(prog)s maintenance "Kernel update and reboot on login0001"
  %(prog)s maintenance "Rebooting login0001" --start "2026-06-01T06:00:00-04:00" --end "2026-06-01T08:00:00-04:00"
  %(prog)s operational "All systems operational"
  %(prog)s outage "login0001 unreachable" --by admin""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("status", choices=VALID_STATUSES, help="New status")
    parser.add_argument("message", help="Status message")
    parser.add_argument("--start", help="Maintenance start time (ISO 8601)")
    parser.add_argument("--end", help="Expected end time (ISO 8601)")
    parser.add_argument("--by", default="chloe", help="Who is making the update (default: chloe)")
    parser.add_argument("--no-generate", action="store_true", help="Skip regenerating the HTML")
    parser.add_argument("--clear-history", action="store_true", help="Clear all history before applying the update")

    args = parser.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    status_file = os.path.join(base, "status.json")

    with open(status_file) as f:
        data = json.load(f)

    if args.clear_history:
        data["history"] = []
        print("History cleared.")

    old = data["current"]

    history_entry = {
        "status": old["status"],
        "message": old["message"],
        "start": old.get("start") or old.get("updated_at", now_iso()),
        "end": now_iso(),
        "updated_by": old.get("updated_by", "system"),
    }
    data.setdefault("history", []).insert(0, history_entry)

    data["current"] = {
        "status": args.status,
        "message": args.message,
        "start": args.start,
        "expected_end": args.end,
        "updated_by": args.by,
        "updated_at": now_iso(),
    }

    with open(status_file, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"Status updated: {args.status} - {args.message}")

    if not args.no_generate:
        subprocess.run([sys.executable, os.path.join(base, "generate.py")], check=True)

if __name__ == "__main__":
    main()
