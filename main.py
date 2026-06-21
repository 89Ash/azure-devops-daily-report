#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ado_client import AzureDevOpsClient
from config import Settings
from query_analyzer import QueryAnalyzer
from report_generator import ReportGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a leadership dashboard from Azure DevOps."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Override REPORT_OUTPUT_DIR from the environment.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated HTML report in the default browser.",
    )
    return parser.parse_args()


def resolve_default_query(
    queries: list[dict],
    preferred: str | None,
    fallback_names: tuple[str, ...],
) -> str:
    if preferred:
        for query in queries:
            if preferred in (query["id"], query["name"], query["path"]):
                return query["id"]
    for name in fallback_names:
        for query in queries:
            if query["name"] == name:
                return query["id"]
    return queries[0]["id"] if queries else ""


def main() -> int:
    args = parse_args()

    try:
        settings = Settings.from_env()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        print("Copy .env.example to .env and fill in your Azure DevOps details.", file=sys.stderr)
        return 1

    output_dir = args.output_dir or settings.output_dir
    client = AzureDevOpsClient(settings)
    analyzer = QueryAnalyzer(
        settings.closed_states,
        excluded_types=settings.excluded_types,
    )
    generator = ReportGenerator()

    print(f"Connecting to {settings.org_url} / project '{settings.project}'...")

    area_analysis = None
    if settings.area_path:
        print(f"  Loading area path: {settings.area_path}...", end=" ", flush=True)
        area_items = client.fetch_area_path_items()
        area_analysis = analyzer.analyze(
            "area-path",
            "Area Path Report",
            settings.area_path,
            area_items,
            scope="area",
        )
        print(f"{area_analysis['item_count']} items ({area_analysis['health']})")
    else:
        print("  No ADO_AREA_PATH set — Area Path tab will be empty.")

    shared_queries = client.list_shared_queries()
    if not shared_queries:
        print("No shared queries found.", file=sys.stderr)
        if not area_analysis:
            return 1

    query_analyses: dict[str, dict] = {}
    sidebar: list[dict] = []

    for index, query in enumerate(shared_queries, start=1):
        print(f"  [{index}/{len(shared_queries)}] {query['name']}...", end=" ", flush=True)
        try:
            items = client.fetch_saved_query_items(query["id"])
            analysis = analyzer.analyze(
                query["id"], query["name"], query["path"], items, scope="query"
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
        except Exception as exc:
            print(f"skipped ({exc})")

    if not query_analyses and not area_analysis:
        print("Could not build any report data.", file=sys.stderr)
        return 1

    default_id = resolve_default_query(
        shared_queries, settings.default_query, settings.fallback_queries
    )
    report_data = generator.build(
        settings.project,
        settings.area_path,
        area_analysis,
        sidebar,
        query_analyses,
        default_id,
    )
    report_path = generator.save_report(report_data, output_dir)

    print("Dashboard generated successfully.")
    if area_analysis:
        print(f"  Area path:       {area_analysis['item_count']} items ({area_analysis['health']})")
    print(f"  Shared queries:  {len(query_analyses)}")
    if query_analyses and default_id in query_analyses:
        print(f"  Default query:   {query_analyses[default_id]['name']}")
    print(f"  Output:          {report_path.resolve()}")

    if args.open:
        import webbrowser

        webbrowser.open(report_path.resolve().as_uri())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
