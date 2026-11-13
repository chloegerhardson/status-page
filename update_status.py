#!/usr/bin/env python3
"""Edit the manual status page and regenerate it.

Examples:
  python3 update_status.py set slurm degraded
  python3 update_status.py note "Job scheduling is slower than normal." \\
      --title "Slow job scheduling" --services slurm
  python3 update_status.py maintenance "Storage maintenance" \\
      --start "2026-11-18T09:00:00-05:00" --end "2026-11-18T13:00:00-05:00" \\
      --services storage,slurm
  python3 update_status.py resolve "Service is restored."
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

VALID_STATES = ["operational", "degraded", "down", "maintenance"]


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path):
    with open(path) as handle:
        return json.load(handle)


def save(path, data):
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def known_ids(data):
    return [service["id"] for service in data["services"]]


def parse_services(value, data):
    if not value:
        return []
    ids = [item.strip() for item in value.split(",") if item.strip()]
    known = set(known_ids(data))
    missing = [item for item in ids if item not in known]
    if missing:
        raise SystemExit(f"Unknown service: {', '.join(missing)}. Known: {', '.join(known_ids(data))}")
    return ids


def set_states(data, service_ids, state):
    for service in data["services"]:
        if service["id"] in service_ids:
            service["state"] = state


def generate(base):
    subprocess.run([sys.executable, os.path.join(base, "generate.py")], check=True)


def prune_maintenance(windows):
    """Keep the newest window and the two scheduled before it."""
    dated = []
    for window in windows:
        dated.append((datetime.fromisoformat(window["start"]), window))
    dated.sort(key=lambda item: item[0])
    return [window for _, window in dated[-3:]]


def main():
    parser = argparse.ArgumentParser(description="Post a manual status update.")
    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set", help="Set one service state without writing a note")
    set_cmd.add_argument("service")
    set_cmd.add_argument("state", choices=VALID_STATES)

    note_cmd = sub.add_parser("note", help="Add the newest incident entry")
    note_cmd.add_argument("text")
    note_cmd.add_argument("--title", required=True)
    note_cmd.add_argument("--services", required=True, help="Comma-separated service ids")
    note_cmd.add_argument("--state", choices=["degraded", "down"], help="Also set those services to this state")

    window_cmd = sub.add_parser("maintenance", help="Publish the next maintenance window")
    window_cmd.add_argument("title")
    window_cmd.add_argument("--start", required=True)
    window_cmd.add_argument("--end", required=True)
    window_cmd.add_argument("--services", required=True)
    window_cmd.add_argument("--text", default="", help="Description shown in the maintenance schedule")

    resolve_cmd = sub.add_parser("resolve", help="Close the open incident and return its services to operational")
    resolve_cmd.add_argument("text")

    args = parser.parse_args()
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "status.json")
    data = load(path)

    if args.command == "set":
        parse_services(args.service, data)
        set_states(data, [args.service], args.state)
        print(f"{args.service} is {args.state}")
    elif args.command == "note":
        service_ids = parse_services(args.services, data)
        incident = data.get("incident") or {"title": args.title, "services": service_ids, "entries": []}
        incident["title"] = args.title
        incident["services"] = service_ids
        incident.setdefault("entries", []).insert(0, {"at": now_iso(), "text": args.text})
        data["incident"] = incident
        if args.state:
            set_states(data, service_ids, args.state)
        print(f"Noted: {args.title}")
    elif args.command == "maintenance":
        service_ids = parse_services(args.services, data)
        data.setdefault("maintenance", []).append({
            "title": args.title,
            "start": args.start,
            "end": args.end,
            "services": service_ids,
            "text": args.text,
        })
        data["maintenance"] = prune_maintenance(data["maintenance"])
        print(f"Scheduled: {args.title}")
    elif args.command == "resolve":
        incident = data.get("incident")
        if not incident:
            raise SystemExit("No open incident to resolve.")
        ended = now_iso()
        entries = incident.get("entries") or []
        started = entries[-1]["at"] if entries else ended
        data.setdefault("history", []).insert(0, {
            "title": incident.get("title") or "Past incident",
            "text": args.text,
            "started": started,
            "ended": ended,
            "services": incident.get("services") or [],
        })
        set_states(data, incident.get("services") or [], "operational")
        data["incident"] = None
        print(f"Resolved: {args.text}")

    save(path, data)
    generate(base)


if __name__ == "__main__":
    main()
