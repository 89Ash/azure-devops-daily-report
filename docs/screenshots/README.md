# Dashboard screenshots

This README is **for humans only** — `setup-guide.html` does **not** read this file.

The setup guide loads **image files** from this folder by name. Until the PNGs exist, the guide shows dashed placeholder boxes (that is normal).

## How it works

```
docs/setup-guide.html  ──looks for──▶  docs/screenshots/01-executive-summary.png
                                       docs/screenshots/02-detailed-view.png
                                       … etc.
```

| File | What to capture |
|------|-----------------|
| `01-executive-summary.png` | Executive Summary panel — KPIs, completion bar, charts |
| `02-detailed-view.png` | Detailed View table with filters and work item columns |
| `03-recommendations.png` | PM Recommendations section |
| `04-sidebar-queries.png` | Left sidebar with shared queries and health dots |
| `05-demo-report.png` | Full browser window after `python main_demo.py --open` |

Use **demo mode** for public screenshots — no real project data:

```bash
python main_demo.py --open
```

## Upload order (GitHub browser)

**Option A — polished repo (recommended)**  
Capture the 5 PNGs locally first, then upload them **together** with the rest of the project (or in a second commit to `docs/screenshots/`).

**Option B — upload code first**  
Upload the repo without PNGs. The setup guide still works — placeholders appear where images will go. Add PNGs later via **Add file → Upload files** in `docs/screenshots/`.

## Viewing the setup guide

| Where | What you see |
|-------|----------------|
| Open `docs/setup-guide.html` locally in Chrome/Safari | Full guide; images appear when PNGs are present |
| GitHub file view of `.html` | Source code only — not a rendered guide |
| GitHub Pages (optional) | Rendered guide with images if PNGs are in the repo |

After images are in place, export PDF: `bash scripts/export-setup-pdf.sh` or Print → Save as PDF.
