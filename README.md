# Login Node Status Page

A static status page for the AICR Cluster login node, built with Python/Jinja2 and deployed via GitHub Pages.

## How It Works

The status page is a static HTML file generated from two inputs:

- **`status.json`** - contains the current status and a history of previous events
- **`template.html`** - a Jinja2 HTML template with a dark theme, status indicator, and history section

When you update the status, `update_status.py` modifies `status.json` (archiving the previous status into history) and runs `generate.py` to render the template into `public/index.html`.

Pushing to `main` triggers a GitHub Actions workflow that regenerates the page and publishes it to GitHub Pages. The workflow automatically attributes the update to whoever pushed the commit.

### Flow

```
update_status.py  -->  status.json  -->  generate.py  -->  public/index.html
                          |                                       |
                   (JSON config file)                    (GitHub Pages serves this)
```

1. Run `update_status.py` with the new status and message
2. The previous status is automatically archived into the history array
3. `generate.py` reads `status.json`, renders `template.html`, writes `public/index.html`
4. Commit and push to `main`
5. GitHub Actions workflow regenerates and deploys to GitHub Pages
6. The "Updated by" field shows whoever triggered the workflow (`github.actor`)

## Quick Start

### Prerequisites

- Python 3.8+
- `jinja2` (`pip install jinja2`)

### Generate and Preview Locally

```bash
cd ~/status-page-github
python3 generate.py
python3 -m http.server 8080 -d public
# Visit http://localhost:8080
```

## Updating the Status

Use `update_status.py` to change the status. It automatically archives the previous status into history and regenerates the page.

### Set a Maintenance Window

```bash
python3 update_status.py maintenance "Kernel update and reboot" \
  --start "2026-06-01T06:00:00-04:00" \
  --end "2026-06-01T08:00:00-04:00"
```

### Report an Outage

```bash
python3 update_status.py outage "Login node unreachable - investigating"
```

### Return to Operational

```bash
python3 update_status.py operational "All systems operational"
```

### Options

| Flag | Description |
|---|---|
| `--start` | Maintenance start time (ISO 8601) |
| `--end` | Expected end time (ISO 8601) |
| `--by` | Who is making the update (default: `chloe`) |
| `--no-generate` | Update `status.json` without regenerating HTML |
| `--clear-history` | Clear all history before applying the update |

### Valid Status Values

| Status | Color | Use Case |
|---|---|---|
| `operational` | Green | Everything is working normally |
| `maintenance` | Yellow | Planned maintenance window |
| `degraded` | Yellow | Partial service issues |
| `outage` | Red | Node is down or unreachable |

## File Structure

```
status-page-github/
├── .github/
│   └── workflows/
│       └── deploy.yml      # GitHub Actions workflow for GitHub Pages
├── generate.py             # Reads status.json, renders template, writes public/index.html
├── update_status.py        # CLI tool to update status and manage history
├── status.json             # Current status + history (managed by update_status.py)
├── template.html           # Jinja2 HTML template (dark theme, status card, history)
├── public/
│   └── index.html          # Generated output (do not edit directly)
└── README.md
```

## GitHub Pages Deployment

The `.github/workflows/deploy.yml` workflow runs on pushes to `main`:

1. Checks out the repo
2. Sets up Python 3.11 and installs `jinja2`
3. Runs `generate.py` with `github.actor` as the "Updated by" value
4. Uploads `public/` and deploys to GitHub Pages

### Setup

1. Go to the repo's **Settings** → **Pages**
2. Set **Source** to **GitHub Actions**

### Typical Workflow

```bash
# 1. Update the status
python3 update_status.py maintenance "Rebooting for kernel update" \
  --start "2026-06-01T06:00:00-04:00" --end "2026-06-01T08:00:00-04:00"

# 2. Commit and push
git add status.json
git commit -m "Set maintenance window for June 1"
git push origin main

# 3. Workflow deploys automatically

# 4. When done, return to operational
python3 update_status.py operational "All systems operational"
git add status.json
git commit -m "Back to operational"
git push origin main
```
