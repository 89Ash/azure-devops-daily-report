#!/usr/bin/env python3
"""Generate a leadership dashboard using demo data.

Use this for presentations and capability demos without connecting to
Azure DevOps or exposing real project insights.

    python main_demo.py
    python main_demo.py --open

Production reports: use main.py instead.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from demo_data import (
    DEFAULT_QUERY_ID,
    DEMO_AREA_PATH,
    DEMO_PROJECT,
    area_path_items,
    query_catalog,
)
from query_analyzer import QueryAnalyzer
from report_generator import ReportGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a demo leadership dashboard with sample data."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Directory for the demo HTML report (default: reports/).",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated demo report in the default browser.",
    )
    return parser.parse_args()


def save_demo_report(generator: ReportGenerator, data, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = data.generated_at.strftime("%Y-%m-%d")
    html_path = output_dir / f"demo-report-{stamp}.html"
    html_path.write_text(generator.render_html(data), encoding="utf-8")
    return html_path


def main() -> int:
    args = parse_args()
    analyzer = QueryAnalyzer(
        closed_states=("Closed", "Done", "Removed", "Resolved"),
        excluded_types=("Task",),
    )
    generator = ReportGenerator()

    print("Generating DEMO dashboard (no Azure DevOps connection)...")
    print(f"  Project:    {DEMO_PROJECT}")
    print(f"  Area path:  {DEMO_AREA_PATH}")

    area_items = area_path_items()
    area_analysis = analyzer.analyze(
        "demo-area-path",
        "Area Path Report",
        DEMO_AREA_PATH,
        area_items,
        scope="area",
    )
    print(
        f"  Area scope: {area_analysis['item_count']} items "
        f"({area_analysis['health']}) — demo data"
    )

    query_analyses: dict[str, dict] = {}
    sidebar: list[dict] = []

    for index, query in enumerate(query_catalog(), start=1):
        print(
            f"  [{index}/{len(query_catalog())}] {query['name']}...",
            end=" ",
            flush=True,
        )
        analysis = analyzer.analyze(
            query["id"],
            query["name"],
            query["path"],
            query["items"],
            scope="query",
        )
        query_analyses[query["id"]] = analysis
        sidebar.append(
            {
                "id": query["id"],
                "name": query["name"],
                "path": query["path"],
                "item_count": analysis["item_count"],
                "health": analysis["health"],
            }
        )
        print(f"{analysis['item_count']} items ({analysis['health']})")

    report_data = generator.build(
        DEMO_PROJECT,
        DEMO_AREA_PATH,
        area_analysis,
        sidebar,
        query_analyses,
        DEFAULT_QUERY_ID,
        show_narrative_footer=True,
    )
    report_path = save_demo_report(generator, report_data, args.output_dir)

    default = query_analyses[DEFAULT_QUERY_ID]
    print()
    print("Demo dashboard generated successfully.")
    print("  ⚠  This report uses FICTIONAL data — not your real Azure DevOps project.")
    print(f"  Area path:       {area_analysis['item_count']} items ({area_analysis['health']})")
    print(f"  Shared queries:  {len(query_analyses)}")
    print(f"  Default query:   {default['name']}")
    print(f"  Output:          {report_path.resolve()}")
    print()
    print("  Switch back to production: python main.py")

    if args.open:
        import webbrowser

        webbrowser.open(report_path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
