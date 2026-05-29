#!/usr/bin/env python3
"""Generate a static status page from status.json and template.html."""

import json
import os
from jinja2 import Environment, FileSystemLoader

STATUS_LABELS = {
    "operational": "Operational",
    "maintenance": "Scheduled Maintenance",
    "degraded": "Degraded Performance",
    "outage": "Service Outage",
}

def main():
    base = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(base, "status.json")) as f:
        data = json.load(f)

    cur = data["current"]
    current_status = cur["status"]

    history = []
    for item in data.get("history", []):
        history.append({
            "status": item["status"],
            "status_display": STATUS_LABELS.get(item["status"], item["status"]),
            "message": item["message"],
            "start_iso": item.get("start", ""),
            "end_iso": item.get("end", ""),
        })

    env = Environment(loader=FileSystemLoader(base))
    template = env.get_template("template.html")

    html = template.render(
        current_status=current_status,
        current_status_display=STATUS_LABELS.get(current_status, current_status),
        current_message=cur["message"],
        current_start_iso=cur.get("start", ""),
        current_end_iso=cur.get("expected_end", ""),
        updated_at_iso=cur.get("updated_at", ""),
        updated_by=os.environ.get("STATUS_UPDATED_BY") or cur.get("updated_by", "system"),
        history=history,
    )

    out_dir = os.path.join(base, "public")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "index.html"), "w") as f:
        f.write(html)

    print(f"Generated {os.path.join(out_dir, 'index.html')}")

if __name__ == "__main__":
    main()
