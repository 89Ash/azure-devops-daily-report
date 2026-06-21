# Azure DevOps Leadership Dashboard

A self-contained HTML leadership dashboard that turns Azure DevOps work items and shared queries into **actionable PM recommendations** — not just another chart.

> *"I didn't build this because I love building tools. I built it because I was tired of spending more time reporting on progress than actually driving it."*

**Yes, Power BI exists. It shows you data. This tells you what to do about it.**

## What it does

- **Area Path Report** — health, KPIs, and trends for your team's scope
- **Shared Queries sidebar** — saved queries with red / amber / green health indicators
- **Executive Summary** — completion %, priority and severity charts, narrative headline
- **Detailed View** — filterable work item table (type, due date, created date, age, and more)
- **PM Recommendations** — decision support, e.g. velocity risk, assignee blockers, overdue items

## Repository

**GitHub:** [github.com/89Ash/azure-devops-daily-report](https://github.com/89Ash/azure-devops-daily-report)

**Setup guide:** open [`docs/setup-guide.html`](docs/setup-guide.html) in a browser for the full step-by-step walkthrough (with screenshots). The GitHub file preview shows HTML source only — download or clone the repo and open the file locally.

## Quick start

### 1. Get the code

```bash
git clone https://github.com/89Ash/azure-devops-daily-report.git
cd azure-devops-daily-report
```

Or download the ZIP from the repository page on GitHub.

### 2. Install and try the demo (no Azure DevOps credentials)

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main_demo.py --open
```

**Windows**

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main_demo.py --open
```

The demo uses fictional data and writes `reports/demo-report-YYYY-MM-DD.html`.

### 3. Connect to your Azure DevOps project

```bash
cp .env.example .env    # Windows: copy .env.example .env
```

Edit `.env` with your org URL, PAT, and project name, then run:

```bash
python main.py --open
```

## Configuration

| Variable | Description |
|----------|-------------|
| `ADO_ORG_URL` | e.g. `https://dev.azure.com/your-org` |
| `ADO_PAT` | Personal access token with **Work Items (Read)** |
| `ADO_PROJECT` | Project name |
| `ADO_AREA_PATH` | Optional team area filter |
| `ADO_CLOSED_STATES` | Default: `Closed,Done,Removed,Resolved` |
| `ADO_EXCLUDED_TYPES` | Child types hidden from tracker (default: `Task`) |
| `ADO_DEFAULT_QUERY` | Optional — shared query name, path, or ID to load first |
| `AZURE_QUERY1` | First fallback query name if `ADO_DEFAULT_QUERY` is not set |
| `AZURE_QUERY2` | Second fallback if `AZURE_QUERY1` is not found |
| `REPORT_OUTPUT_DIR` | Default: `reports/` |

**Query names:** `AZURE_QUERY1`, `AZURE_QUERY2`, and `ADO_DEFAULT_QUERY` must **exactly match** the query name shown under **Boards → Queries → Shared Queries** in Azure DevOps (not the folder path).

**Tags:** work items tagged `customer-reported` feed into customer triage insights.

**Security:** never commit `.env` — it contains your PAT. Only `.env.example` (with placeholders) belongs in the repository.

## Project layout

| Path | Purpose |
|------|---------|
| `main.py` | Generate dashboard from live Azure DevOps data |
| `main_demo.py` | Generate dashboard from sample data (no credentials) |
| `ado_client.py` | Azure DevOps REST API client |
| `query_analyzer.py` | KPIs, health, trends, recommendations |
| `report_generator.py` | HTML dashboard renderer |
| `docs/setup-guide.html` | User setup guide |
| `docs/screenshots/` | Guide illustrations |

## Scheduling (optional)

To run reports on a schedule, use any scheduler you prefer (cron, Task Scheduler, GitHub Actions, n8n, etc.) to execute `python main.py` from the project directory with the virtual environment activated.

A generic macOS launchd template is included: `com.example.ado-daily-report.plist.example` — copy and edit paths before use.

## Troubleshooting

See the **Troubleshooting** section in [`docs/setup-guide.html`](docs/setup-guide.html) for common issues (missing config, PAT errors, blank columns, query name mismatches, and Azure field reference names).

## Why this, not a BI tool?

The barrier to PMs building their own decision-support tools has collapsed — Python, a PAT, and a template get you from raw ADO data to *here's what to do Monday morning*.

## Roadmap

- Predictive sprint risk scoring
- Automated escalation when assignee blockers or velocity slips exceed thresholds
