#!/usr/bin/env bash
# Export docs/setup-guide.html to PDF (macOS — uses Chrome headless).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HTML="$ROOT/docs/setup-guide.html"
PDF="$ROOT/docs/Azure-DevOps-Dashboard-Setup-Guide.pdf"

CHROME=""
for candidate in \
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  "/Applications/Chromium.app/Contents/MacOS/Chromium" \
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"; do
  if [[ -x "$candidate" ]]; then
    CHROME="$candidate"
    break
  fi
done

if [[ -z "$CHROME" ]]; then
  echo "Chrome/Chromium/Edge not found."
  echo "Open docs/setup-guide.html in any browser and use Print → Save as PDF."
  exit 1
fi

"$CHROME" \
  --headless=new \
  --disable-gpu \
  --no-pdf-header-footer \
  --print-to-pdf="$PDF" \
  "file://$HTML"

echo "PDF written to: $PDF"
