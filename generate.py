#!/usr/bin/env python3
"""Generate a static status page from status.json and template.html."""

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

EASTERN = ZoneInfo("America/New_York")

STATE_LABELS = {
    "operational": "Operational",
    "degraded": "Degraded",
    "down": "Down",
    "maintenance": "Maintenance",
}

STATE_RANK = {
    "operational": 0,
    "maintenance": 1,
    "degraded": 2,
    "down": 3,
}


def parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def format_et(value):
    moment = parse_dt(value)
    if moment is None:
        return ""
    local = moment.astimezone(EASTERN)
    hour = local.strftime("%I").lstrip("0") or "12"
    return f"{local.strftime('%b')} {local.day}, {hour}:{local.strftime('%M %p')} {local.tzname()}"


def format_day(value):
    moment = parse_dt(value)
    if moment is None:
        return ""
    local = moment.astimezone(EASTERN)
    return f"{local.strftime('%b')} {local.day}"


def format_clock(value):
    moment = parse_dt(value)
    if moment is None:
        return ""
    local = moment.astimezone(EASTERN)
    hour = local.strftime("%I").lstrip("0") or "12"
    return f"{hour}:{local.strftime('%M %p')}"


def format_duration(start, end):
    if start is None or end is None:
        return ""
    minutes = int((end - start).total_seconds() // 60)
    if minutes < 1:
        return "under 1m"
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def join_names(names):
    names = [name for name in names if name]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def service_name(services, service_id):
    for service in services:
        if service["id"] == service_id:
            return service["name"]
    return service_id


def active_maintenance(windows, now):
    active = []
    for window in windows:
        start = parse_dt(window.get("start"))
        end = parse_dt(window.get("end"))
        if start and end and start <= now < end:
            active.append(window)
    return active


def next_maintenance(windows, now):
    upcoming = []
    for window in windows:
        end = parse_dt(window.get("end"))
        start = parse_dt(window.get("start"))
        if end and end > now:
            upcoming.append((start or end, window))
    if not upcoming:
        return None
    upcoming.sort(key=lambda item: item[0])
    return upcoming[0][1]


def kept_maintenance(windows):
    """The newest window, plus the two scheduled before it."""
    dated = []
    for window in windows:
        start = parse_dt(window.get("start"))
        if start:
            dated.append((start, window))
    dated.sort(key=lambda item: item[0])
    if len(dated) <= 3:
        return [window for _, window in dated]
    return [window for _, window in dated[-3:]]


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base, "status.json")) as handle:
        data = json.load(handle)

    now = datetime.now().astimezone()
    services = data["services"]
    names = {service["id"]: service["name"] for service in services}
    windows = data.get("maintenance") or []
    active = active_maintenance(windows, now)
    active_ids = {service_id for window in active for service_id in window.get("services", [])}

    rows = []
    for service in services:
        state = "maintenance" if service["id"] in active_ids else service["state"]
        link = service.get("link") or {}
        if state == "operational":
            link_label = link.get("label", "Documentation")
            link_href = link.get("href", "https://docs.aicr.ai/")
            link_kind = "external"
        elif state == "maintenance":
            link_label = "Maintenance details"
            link_href = ""
            link_kind = "maintenance"
        else:
            link_label = "Incident details"
            link_href = ""
            link_kind = "incident"
        rows.append({
            "name": service["name"],
            "summary": service.get("summary", ""),
            "state": state,
            "state_label": STATE_LABELS.get(state, state),
            "link_label": link_label,
            "link_href": link_href,
            "link_kind": link_kind,
        })

    worst = max(rows, key=lambda row: STATE_RANK.get(row["state"], 0))["state"]
    affected = [row["name"] for row in rows if row["state"] == worst and worst != "operational"]

    incident = data.get("incident")
    entries = []
    if incident:
        entries = sorted(
            incident.get("entries") or [],
            key=lambda entry: parse_dt(entry.get("at")) or datetime.min.replace(tzinfo=EASTERN),
            reverse=True,
        )
    latest_text = entries[0]["text"] if entries else ""

    if worst == "operational":
        banner_text = "All services operational"
        show_update_link = False
    else:
        banner_text = f"{STATE_LABELS[worst]}: {join_names(affected)}."
        if worst == "maintenance" and active:
            banner_text = f"{banner_text} {active[0]['title']}"
        elif latest_text:
            banner_text = f"{banner_text} {latest_text}"
        show_update_link = True

    incident_view = None
    if incident and entries and worst != "operational":
        incident_view = {
            "title": incident.get("title") or "Service update",
            "meta": "Updated "
            + format_et(entries[0].get("at"))
            + " · "
            + join_names(names.get(service_id, service_id) for service_id in incident.get("services", [])),
            "label": "Investigating" if worst != "down" else "Down",
            "entries": [
                {"when": format_et(entry.get("at")), "text": entry.get("text") or ""}
                for entry in entries
            ],
        }

    def window_meta(window):
        start = window.get("start")
        end = window.get("end")
        start_dt = parse_dt(start)
        end_dt = parse_dt(end)
        zone = end_dt.astimezone(EASTERN).tzname() if end_dt else "ET"
        if start_dt and end_dt and start_dt.astimezone(EASTERN).date() != end_dt.astimezone(EASTERN).date():
            when = f"{format_et(start)} to {format_et(end)}"
        else:
            when = f"{format_day(start)}, {format_clock(start)} to {format_clock(end)} {zone}"
        service_ids = window.get("services") or []
        if service_ids and set(service_ids) == set(names):
            covered = "All services"
        else:
            covered = join_names(names.get(service_id, service_id) for service_id in service_ids)
        if covered:
            when = f"{when} · {covered}"
        return when

    upcoming = next_maintenance(windows, now)
    maintenance_view = None
    if upcoming:
        maintenance_view = {
            "title": upcoming.get("title") or "Scheduled maintenance",
            "meta": window_meta(upcoming),
            "label": "Scheduled",
        }

    maintenance_schedule = []
    for window in reversed(kept_maintenance(windows)):
        end = parse_dt(window.get("end"))
        scheduled = bool(end and end > now)
        maintenance_schedule.append({
            "title": window.get("title") or "Scheduled maintenance",
            "when": window_meta(window),
            "text": window.get("text") or "",
            "label": "Scheduled" if scheduled else "Completed",
        })

    history_view = []
    for item in data.get("history") or []:
        started = parse_dt(item.get("started"))
        ended = parse_dt(item.get("ended"))
        meta = format_day(item.get("ended") or item.get("started"))
        duration = format_duration(started, ended)
        if duration:
            meta = f"{meta} · {duration}"
        covered = join_names(names.get(service_id, service_id) for service_id in item.get("services", []))
        if covered:
            meta = f"{meta} · {covered}"
        history_view.append({
            "title": item.get("title") or "Past incident",
            "meta": meta,
            "label": "Resolved",
        })

    links = data.get("links") or {}
    env = Environment(loader=FileSystemLoader(base), autoescape=True)
    html = env.get_template("template.html").render(
        banner_state=worst,
        banner_text=banner_text,
        show_update_link=show_update_link,
        services=rows,
        incident=incident_view,
        maintenance=maintenance_view,
        maintenance_schedule=maintenance_schedule,
        history=history_view,
        show_updates=bool(incident_view or maintenance_view or history_view),
        documentation=links.get("documentation", "https://docs.aicr.ai/"),
        help_link=links.get("help", "https://docs.aicr.ai/getting-help/"),
    )

    out_dir = os.path.join(base, "public")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w") as handle:
        handle.write(html)
    print(f"Generated {out_path}")


if __name__ == "__main__":
    main()
