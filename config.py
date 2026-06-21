from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CLOSED_STATES = ("Closed", "Done", "Removed", "Resolved")
DEFAULT_DEFECT_TYPES = ("Bug", "Defect")
DEFAULT_EXCLUDED_TYPES = ("Task",)
DEFAULT_HIGH_PRIORITY_LEVELS = (1, 2)
DEFAULT_FIELDS = (
    "System.Id",
    "System.Title",
    "System.State",
    "System.WorkItemType",
    "Microsoft.VSTS.Common.Priority",
    "Microsoft.VSTS.Common.Severity",
    "System.IterationPath",
    "System.AreaPath",
    "System.AssignedTo",
    "System.CreatedDate",
    "System.ChangedDate",
    "Microsoft.VSTS.Scheduling.DueDate",
    "Microsoft.VSTS.Scheduling.TargetDate",
    "System.Tags",
)


@dataclass(frozen=True)
class Settings:
    org_url: str
    pat: str
    project: str
    area_path: str | None
    closed_states: tuple[str, ...]
    defect_types: tuple[str, ...]
    excluded_types: tuple[str, ...]
    high_priority_levels: tuple[int, ...]
    default_query: str | None
    fallback_queries: tuple[str, ...]
    output_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        org_url = os.environ.get("ADO_ORG_URL", "").rstrip("/")
        pat = os.environ.get("ADO_PAT", "")
        project = os.environ.get("ADO_PROJECT", "")

        if not org_url or not pat or not project:
            raise ValueError(
                "Missing required environment variables: ADO_ORG_URL, ADO_PAT, ADO_PROJECT"
            )

        area_path = os.environ.get("ADO_AREA_PATH") or None
        closed_raw = os.environ.get("ADO_CLOSED_STATES", "")
        closed_states = (
            tuple(s.strip() for s in closed_raw.split(",") if s.strip())
            if closed_raw
            else DEFAULT_CLOSED_STATES
        )
        defect_raw = os.environ.get("ADO_DEFECT_TYPES", "")
        defect_types = (
            tuple(t.strip() for t in defect_raw.split(",") if t.strip())
            if defect_raw
            else DEFAULT_DEFECT_TYPES
        )
        excluded_raw = os.environ.get("ADO_EXCLUDED_TYPES", "")
        excluded_types = (
            tuple(t.strip() for t in excluded_raw.split(",") if t.strip())
            if excluded_raw
            else DEFAULT_EXCLUDED_TYPES
        )
        priority_raw = os.environ.get("ADO_HIGH_PRIORITY_LEVELS", "")
        high_priority_levels = (
            tuple(int(level.strip()) for level in priority_raw.split(",") if level.strip())
            if priority_raw
            else DEFAULT_HIGH_PRIORITY_LEVELS
        )
        default_query = os.environ.get("ADO_DEFAULT_QUERY") or None
        azure_query1 = os.environ.get("AZURE_QUERY1", "").strip()
        azure_query2 = os.environ.get("AZURE_QUERY2", "").strip()
        fallback_queries = tuple(
            name for name in (azure_query1, azure_query2) if name
        )
        output_dir = Path(os.environ.get("REPORT_OUTPUT_DIR", "reports"))

        return cls(
            org_url=org_url,
            pat=pat,
            project=project,
            area_path=area_path,
            closed_states=closed_states,
            defect_types=defect_types,
            excluded_types=excluded_types,
            high_priority_levels=high_priority_levels,
            default_query=default_query,
            fallback_queries=fallback_queries,
            output_dir=output_dir,
        )
