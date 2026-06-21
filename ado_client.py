from __future__ import annotations

import base64
from typing import Any

import requests

from config import DEFAULT_FIELDS, Settings


class AzureDevOpsClient:
    API_VERSION = "7.1"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        token = base64.b64encode(f":{settings.pat}".encode()).decode()
        self.session.headers.update(
            {
                "Authorization": f"Basic {token}",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return f"{self.settings.org_url}/{path.lstrip('/')}"

    def run_wiql(self, query: str) -> list[int]:
        url = self._url(
            f"{self.settings.project}/_apis/wit/wiql?api-version={self.API_VERSION}"
        )
        response = self.session.post(url, json={"query": query}, timeout=60)
        if not response.ok:
            message = response.text
            try:
                message = response.json().get("message", message)
            except ValueError:
                pass
            raise requests.HTTPError(
                f"{response.status_code} {response.reason}: {message}",
                response=response,
            )
        payload = response.json()
        return [item["id"] for item in payload.get("workItems", [])]

    def get_work_items(self, ids: list[int], fields: tuple[str, ...] = DEFAULT_FIELDS) -> list[dict[str, Any]]:
        if not ids:
            return []

        items: list[dict[str, Any]] = []
        batch_size = 200
        for start in range(0, len(ids), batch_size):
            batch = ids[start : start + batch_size]
            ids_param = ",".join(str(item_id) for item_id in batch)
            fields_param = ",".join(fields)
            url = self._url(
                f"_apis/wit/workitems?ids={ids_param}&fields={fields_param}"
                f"&api-version={self.API_VERSION}"
            )
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            for work_item in response.json().get("value", []):
                items.append(self._normalize_work_item(work_item, self.settings.closed_states))
        return items

    def fetch_active_work_items(self) -> list[dict[str, Any]]:
        query = self._build_active_query()
        ids = self.run_wiql(query)
        return self.get_work_items(ids)

    def fetch_all_work_items_for_milestones(self) -> list[dict[str, Any]]:
        query = self._build_milestone_query()
        ids = self.run_wiql(query)
        return self.get_work_items(ids)

    def fetch_high_priority_defects(self) -> list[dict[str, Any]]:
        query = self._build_defect_query()
        ids = self.run_wiql(query)
        return self.get_work_items(ids)

    def list_shared_queries(self) -> list[dict[str, Any]]:
        url = self._url(
            f"{self.settings.project}/_apis/wit/queries?api-version={self.API_VERSION}&$depth=2"
        )
        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        queries: list[dict[str, Any]] = []

        def walk(node: dict[str, Any], path: str) -> None:
            name = node.get("name", "")
            full_path = f"{path}/{name}" if path else name
            if node.get("isFolder"):
                for child in node.get("children") or []:
                    walk(child, full_path)
            else:
                queries.append(
                    {
                        "id": node["id"],
                        "name": name,
                        "path": full_path,
                    }
                )

        for folder in response.json().get("value", []):
            if folder.get("name") == "Shared Queries":
                for child in folder.get("children") or []:
                    walk(child, "Shared Queries")
        return queries

    def run_saved_query(self, query_id: str) -> list[int]:
        url = self._url(
            f"{self.settings.project}/_apis/wit/wiql/{query_id}?api-version={self.API_VERSION}"
        )
        response = self.session.get(url, timeout=60)
        if not response.ok:
            message = response.text
            try:
                message = response.json().get("message", message)
            except ValueError:
                pass
            raise requests.HTTPError(
                f"{response.status_code} {response.reason}: {message}",
                response=response,
            )
        return [item["id"] for item in response.json().get("workItems", [])]

    def fetch_saved_query_items(self, query_id: str) -> list[dict[str, Any]]:
        ids = self.run_saved_query(query_id)
        return self.get_work_items(ids)

    def fetch_area_path_items(self) -> list[dict[str, Any]]:
        if not self.settings.area_path:
            return []
        query = self._build_area_path_query()
        ids = self.run_wiql(query)
        return self.get_work_items(ids)

    def _build_area_path_query(self) -> str:
        return f"""
SELECT [System.Id]
FROM WorkItems
WHERE [System.TeamProject] = '{self._escape_wiql(self.settings.project)}'
  AND [System.AreaPath] UNDER '{self.settings.area_path}'
ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [System.State] ASC
""".strip()

    def _build_active_query(self) -> str:
        closed = ", ".join(f"'{state}'" for state in self.settings.closed_states)
        area_filter = ""
        if self.settings.area_path:
            area_filter = f"\n  AND [System.AreaPath] UNDER '{self.settings.area_path}'"

        return f"""
SELECT [System.Id]
FROM WorkItems
WHERE [System.TeamProject] = '{self._escape_wiql(self.settings.project)}'
  AND [System.State] NOT IN ({closed}){area_filter}
ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [Microsoft.VSTS.Scheduling.DueDate] ASC
""".strip()

    def _build_defect_query(self) -> str:
        types = ", ".join(
            f"'{self._escape_wiql(defect_type)}'"
            for defect_type in self.settings.defect_types
        )
        priorities = ", ".join(
            str(level) for level in self.settings.high_priority_levels
        )
        area_filter = ""
        if self.settings.area_path:
            area_filter = f"\n  AND [System.AreaPath] UNDER '{self.settings.area_path}'"

        return f"""
SELECT [System.Id]
FROM WorkItems
WHERE [System.TeamProject] = '{self._escape_wiql(self.settings.project)}'
  AND [System.WorkItemType] IN ({types})
  AND [Microsoft.VSTS.Common.Priority] IN ({priorities}){area_filter}
ORDER BY [Microsoft.VSTS.Common.Priority] ASC, [System.State] ASC
""".strip()

    def _build_milestone_query(self) -> str:
        area_filter = ""
        if self.settings.area_path:
            area_filter = f"\n  AND [System.AreaPath] UNDER '{self.settings.area_path}'"

        return f"""
SELECT [System.Id]
FROM WorkItems
WHERE [System.TeamProject] = '{self._escape_wiql(self.settings.project)}'
  AND [System.IterationPath] <> ''{area_filter}
ORDER BY [System.IterationPath] ASC
""".strip()

    @staticmethod
    def _escape_wiql(value: str) -> str:
        return value.replace("'", "''")

    @staticmethod
    def _normalize_work_item(
        work_item: dict[str, Any], closed_states: tuple[str, ...]
    ) -> dict[str, Any]:
        fields = work_item.get("fields", {})
        assigned = fields.get("System.AssignedTo")
        assignee = None
        if isinstance(assigned, dict):
            assignee = assigned.get("displayName")
        elif isinstance(assigned, str):
            assignee = assigned

        due_date = (
            fields.get("Microsoft.VSTS.Scheduling.DueDate")
            or fields.get("Microsoft.VSTS.Scheduling.TargetDate")
            or fields.get("System.DueDate")
        )

        return {
            "id": work_item.get("id"),
            "title": fields.get("System.Title", ""),
            "state": fields.get("System.State", ""),
            "type": fields.get("System.WorkItemType", ""),
            "priority": fields.get("Microsoft.VSTS.Common.Priority"),
            "severity": fields.get("Microsoft.VSTS.Common.Severity"),
            "due_date": due_date,
            "iteration": fields.get("System.IterationPath", ""),
            "area": fields.get("System.AreaPath", ""),
            "assignee": assignee,
            "created": fields.get("System.CreatedDate"),
            "changed": fields.get("System.ChangedDate"),
            "tags": fields.get("System.Tags", "") or "",
            "url": work_item.get("url", "").replace("_apis/wit/workItems", "_workitems/edit"),
            "is_closed": fields.get("System.State", "") in set(closed_states),
        }
