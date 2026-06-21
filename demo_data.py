from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# Fictional demo project — clearly not real ADO data
DEMO_PROJECT = "Sample Project"
DEMO_AREA_PATH = "Sample Project/AreaPath"
DEMO_ORG_URL = "https://dev.azure.com/demo-org"

CLOSED_STATES = {"Closed", "Done", "Resolved"}


def _days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _item(
    item_id: int,
    title: str,
    state: str,
    work_type: str,
    priority: int,
    severity: str,
    assignee: str,
    *,
    due_days: int | None = None,
    created_days: int = 14,
    changed_days: int = 1,
    iteration: str = "Sample Project/Sprint 14",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    due_date = None
    if due_days is not None:
        due_date = (today + timedelta(days=due_days)).isoformat()

    return {
        "id": item_id,
        "title": title,
        "state": state,
        "type": work_type,
        "priority": priority,
        "severity": severity,
        "due_date": due_date,
        "iteration": iteration,
        "area": DEMO_AREA_PATH,
        "assignee": assignee,
        "tags": "; ".join(tags) if tags else "",
        "created": _days_ago(created_days),
        "changed": _days_ago(changed_days),
        "url": f"{DEMO_ORG_URL}/sample-project/_workitems/edit/{item_id}",
        "is_closed": state in CLOSED_STATES,
    }


def _task(item_id: int, title: str, assignee: str) -> dict[str, Any]:
    """Child tasks are included in raw sets but filtered out by QueryAnalyzer."""
    return _item(
        item_id,
        title,
        "Active",
        "Task",
        3,
        "3 - Medium",
        assignee,
        created_days=5,
        changed_days=2,
    )


def area_path_items() -> list[dict[str, Any]]:
    return [
        _item(5001, "Checkout flow fails on mobile Safari", "Active", "Bug", 1, "1 - Critical", "Alex Rivera", due_days=-2, created_days=21, changed_days=4, tags=["customer-reported"]),
        _item(5002, "Payment gateway timeout under peak load", "PR Review", "Bug", 1, "1 - Critical", "Jordan Kim", due_days=1, created_days=18, changed_days=0),
        _item(5003, "Loyalty points not syncing after purchase", "New", "Bug", 1, "1 - Critical", "Sam Patel", due_days=3, created_days=10, changed_days=8, tags=["customer-reported"]),
        _item(5004, "Implement SSO for enterprise tenants", "Active", "User Story", 2, "2 - High", "Morgan Lee", due_days=5, created_days=30, changed_days=2),
        _item(5005, "Dashboard widgets render blank on first load", "Active", "Bug", 2, "2 - High", "Alex Rivera", due_days=-1, created_days=12, changed_days=4),
        _item(5006, "Migrate notification service to event bus", "PR Review", "User Story", 2, "2 - High", "Taylor Brooks", due_days=7, created_days=25, changed_days=1),
        _item(5007, "Accessibility audit — keyboard navigation gaps", "New", "User Story", 2, "2 - High", "Unassigned", due_days=10, created_days=6, changed_days=6),
        _item(5008, "Export CSV truncates large datasets", "Closed", "Bug", 2, "2 - High", "Jordan Kim", created_days=20, changed_days=2),
        _item(5009, "Profile avatar upload fails for PNG > 2MB", "Closed", "Bug", 1, "1 - Critical", "Sam Patel", created_days=15, changed_days=4),
        _item(5010, "Add dark mode toggle to settings panel", "Closed", "User Story", 3, "3 - Medium", "Morgan Lee", created_days=40, changed_days=3),
        _item(5011, "Refactor cart state management", "Closed", "User Story", 3, "3 - Medium", "Taylor Brooks", created_days=35, changed_days=5),
        _item(5012, "Update API rate-limit documentation", "Closed", "Bug", 4, "4 - Low", "Alex Rivera", created_days=50, changed_days=6),
        _item(5013, "Spike: evaluate GraphQL vs REST for catalog", "Active", "User Story", 3, "3 - Medium", "Morgan Lee", due_days=14, created_days=8, changed_days=9),
        _item(5014, "Write unit tests for discount engine", "New", "User Story", 3, "3 - Medium", "Taylor Brooks", due_days=12, created_days=4, changed_days=4),
        _item(5015, "Safari autofill breaks checkout on iPad", "Active", "Bug", 2, "2 - High", "Alex Rivera", due_days=6, created_days=16, changed_days=5),
        _item(5016, "Cart badge count stale after item removal", "New", "Bug", 3, "3 - Medium", "Alex Rivera", due_days=11, created_days=9, changed_days=4),
        _item(5017, "Customer-reported: receipt email missing tax line", "Closed", "Bug", 2, "2 - High", "Jordan Kim", created_days=48, changed_days=3, tags=["customer-reported"]),
        _item(5018, "Customer-reported: promo code rejected at checkout", "Closed", "Bug", 2, "2 - High", "Sam Patel", created_days=42, changed_days=5, tags=["customer-reported"]),
        # Child tasks — excluded from tracker view
        _task(5091, "Reproduce Safari checkout bug on iOS 17", "Alex Rivera"),
        _task(5092, "Add integration test for loyalty sync", "Sam Patel"),
        _task(5093, "Update SSO config in staging", "Morgan Lee"),
    ]


def query_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "demo-query-release-blockers",
            "name": "Release Blockers",
            "path": "Shared Queries/Release Blockers",
            "items": [
                _item(6001, "Production login regression — OAuth redirect loop", "Active", "Bug", 1, "1 - Critical", "Alex Rivera", due_days=-3, created_days=5, changed_days=0),
                _item(6002, "Data migration script corrupts user preferences", "PR Review", "Bug", 1, "1 - Critical", "Jordan Kim", due_days=0, created_days=8, changed_days=1),
                _item(6003, "API v2 backward compatibility break", "New", "Bug", 1, "1 - Critical", "Sam Patel", due_days=2, created_days=3, changed_days=3),
                _item(6004, "Rollback plan not documented for v4.2", "Active", "User Story", 2, "2 - High", "Morgan Lee", due_days=1, created_days=7, changed_days=2),
                _item(6005, "Load test failures at 10k concurrent users", "Closed", "Bug", 1, "1 - Critical", "Taylor Brooks", created_days=12, changed_days=2),
                _item(6006, "Certificate expiry monitoring gap", "Closed", "Bug", 2, "2 - High", "Alex Rivera", created_days=20, changed_days=4),
            ],
        },
        {
            "id": "demo-query-sprint-priority",
            "name": "Sprint 12 Priority Items",
            "path": "Shared Queries/Sprint 12 Priority Items",
            "items": [
                _item(6101, "Checkout flow fails on mobile Safari", "Active", "Bug", 1, "1 - Critical", "Alex Rivera", due_days=-2, created_days=21, changed_days=1),
                _item(6102, "Payment gateway timeout under peak load", "PR Review", "Bug", 1, "1 - Critical", "Jordan Kim", due_days=1, created_days=18, changed_days=0),
                _item(6103, "Implement SSO for enterprise tenants", "Active", "User Story", 2, "2 - High", "Morgan Lee", due_days=5, created_days=30, changed_days=2),
                _item(6104, "Dashboard widgets render blank on first load", "Active", "Bug", 2, "2 - High", "Alex Rivera", due_days=-1, created_days=12, changed_days=3),
                _item(6105, "Accessibility audit — keyboard navigation gaps", "New", "User Story", 2, "2 - High", "Unassigned", due_days=10, created_days=6, changed_days=6),
                _item(6106, "Export CSV truncates large datasets", "Closed", "Bug", 2, "2 - High", "Jordan Kim", created_days=20, changed_days=2),
                _item(6107, "Add dark mode toggle to settings panel", "Closed", "User Story", 3, "3 - Medium", "Morgan Lee", created_days=40, changed_days=3),
            ],
        },
        {
            "id": "demo-query-customer-feedback",
            "name": "Customer Feedback Backlog",
            "path": "Shared Queries/Customer Feedback Backlog",
            "items": [
                _item(6301, "Users request bulk edit for team members", "New", "User Story", 2, "2 - High", "Morgan Lee", due_days=14, created_days=20, changed_days=10, tags=["customer-reported"]),
                _item(6302, "Support ticket: cannot reset 2FA without admin", "Active", "Bug", 2, "2 - High", "Unassigned", due_days=7, created_days=5, changed_days=5, tags=["customer-reported"]),
                _item(6303, "Feature request: scheduled report exports", "New", "User Story", 3, "3 - Medium", "Taylor Brooks", due_days=21, created_days=15, changed_days=12),
                _item(6304, "Intermittent 503 on webhook delivery", "Active", "Bug", 1, "1 - Critical", "Jordan Kim", due_days=2, created_days=4, changed_days=1),
                _item(6305, "Customer-reported: login page error on mobile", "Closed", "Bug", 2, "2 - High", "Jordan Kim", created_days=50, changed_days=2, tags=["customer-reported"]),
                _item(6306, "Customer-reported: invoice PDF formatting broken", "Closed", "Bug", 2, "2 - High", "Sam Patel", created_days=44, changed_days=4, tags=["customer-reported"]),
                _item(6307, "Internal: refactor notification templates", "Closed", "User Story", 3, "3 - Medium", "Taylor Brooks", created_days=18, changed_days=3),
            ],
        },
        {
            "id": "demo-query-tech-debt",
            "name": "Platform Tech Debt",
            "path": "Shared Queries/Platform Tech Debt",
            "items": [
                _item(6401, "Upgrade React 17 → 18 across micro-frontends", "Active", "User Story", 3, "3 - Medium", "Alex Rivera", due_days=30, created_days=60, changed_days=14),
                _item(6402, "Replace deprecated Azure SDK calls", "New", "User Story", 3, "3 - Medium", "Sam Patel", due_days=45, created_days=45, changed_days=20),
                _item(6403, "Consolidate duplicate auth middleware", "Active", "User Story", 2, "2 - High", "Morgan Lee", due_days=21, created_days=30, changed_days=8),
                _item(6404, "Remove legacy feature flags (pre-v3.0)", "Closed", "User Story", 4, "4 - Low", "Taylor Brooks", created_days=90, changed_days=6),
                _item(6405, "Database index optimization for orders table", "PR Review", "User Story", 2, "2 - High", "Jordan Kim", due_days=10, created_days=22, changed_days=2),
            ],
        },
        {
            "id": "demo-query-regression-suite",
            "name": "Regression Suite Failures",
            "path": "Shared Queries/Regression Suite Failures",
            "items": [
                _item(6501, "E2E: login flow flaky in CI pipeline", "Active", "Bug", 2, "2 - High", "Alex Rivera", due_days=4, created_days=7, changed_days=1),
                _item(6502, "Unit: discount calculation off by 0.01", "Closed", "Bug", 2, "2 - High", "Jordan Kim", created_days=5, changed_days=1),
                _item(6503, "Integration: webhook retry logic not firing", "New", "Bug", 1, "1 - Critical", "Sam Patel", due_days=3, created_days=2, changed_days=2),
            ],
        },
    ]

DEFAULT_QUERY_ID = "demo-query-sprint-priority"
