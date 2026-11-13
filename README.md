# AICR status

A static status page for the AICR cluster. People publish the note, the next maintenance window, and the service states in `status.json`. GitHub Actions rebuilds the page and GitHub Pages serves it.

The page shows the next maintenance window. Maintenance schedule opens the next window and the two before it. Adding a newer window drops the oldest. A service inside a published maintenance window shows Maintenance while that window is open.

`status.json` currently holds a sample incident so the manual update is visible. Replace it before treating the page as live.

## Update the page

```bash
python3 update_status.py set slurm degraded
python3 update_status.py note "Job scheduling is slower than normal. We are investigating." \
  --title "Slow job scheduling" --services slurm --state degraded
python3 update_status.py maintenance "Storage maintenance" \
  --start "2026-11-18T09:00:00-05:00" --end "2026-11-18T13:00:00-05:00" \
  --services storage,slurm
python3 update_status.py resolve "Service is restored."
```

`set` changes a service and does not write a note. `note` adds the newest incident entry. `resolve` moves that incident into history and sets its services back to operational.

Commit `status.json` and push to `main`. The Deploy Status Page workflow regenerates `public/index.html` and publishes it.

## Preview locally

```bash
python3 generate.py
python3 -m http.server 8080 -d public
```

## States

| State | Meaning |
|---|---|
| operational | A user can do the normal work of that service |
| degraded | A user can still do some of that work |
| down | A user cannot do that work |
| maintenance | The service is inside a published window |

The banner is the worst state currently in effect: down, then degraded, then maintenance, then operational.
