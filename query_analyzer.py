from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

PRIORITY_LABELS = {1: "Critical", 2: "High", 3: "Medium", 4: "Low"}
PRIORITY_ORDER = (1, 2, 3, 4, 5)
SEVERITY_ORDER = ("Critical", "High", "Medium", "Low")
SEVERITY_RANK = {label: index for index, label in enumerate(SEVERITY_ORDER, start=1)}
STATE_TAB_ORDER = ("New", "Active", "PR Review", "Ready", "Resolved", "Closed", "Done")
INSIGHT_TAB_ORDER = (
    ("closed-this-week", "Closed this week"),
    ("overdue", "Overdue"),
    ("at-risk", "At risk"),
    ("stale", "Stale (7+ days)"),
    ("unassigned", "Unassigned"),
    ("critical", "Critical (P1)"),
    ("high-priority", "High (P2)"),
    ("customer-reported", "Customer-reported"),
)


class QueryAnalyzer:
    TRACKER_TITLE = "High Priority Items Tracker"
    TRACKER_SUBTITLE = (
        "User stories, bugs, and other parent work items — excluding child tasks. "
        "Tracks open items, resolution progress, and recent closures."
    )

    def __init__(
        self,
        closed_states: tuple[str, ...],
        excluded_types: tuple[str, ...] = ("Task",),
    ) -> None:
        self.closed_states = set(closed_states)
        self.excluded_types = set(excluded_types)

    def analyze(
        self,
        scope_id: str,
        name: str,
        path: str,
        items: list[dict[str, Any]],
        scope: str = "query",
        today: date | None = None,
    ) -> dict[str, Any]:
        today = today or datetime.now(timezone.utc).date()
        week_ago = today - timedelta(days=7)
        items = self._exclude_child_tasks(items)

        open_items: list[dict[str, Any]] = []
        closed_items: list[dict[str, Any]] = []
        recently_closed: list[dict[str, Any]] = []

        for item in items:
            if item.get("state") in self.closed_states:
                closed_items.append(item)
                changed = self._parse_date(item.get("changed"))
                if changed is not None and changed >= week_ago:
                    recently_closed.append(item)
            else:
                open_items.append(item)

        total = len(items)
        open_count = len(open_items)
        closed_count = len(closed_items)
        completion_pct = round((closed_count / total) * 100, 1) if total else 0.0

        critical_open = sum(1 for item in open_items if self._priority_rank(item) == 1)
        high_open = sum(1 for item in open_items if self._priority_rank(item) == 2)
        in_review = sum(1 for item in open_items if item.get("state") == "PR Review")
        overdue = sum(
            1 for item in open_items if self._due_status(item, today) == "overdue"
        )
        at_risk = sum(
            1
            for item in open_items
            if self._priority_rank(item) <= 2
            and self._due_status(item, today) in ("overdue", "due_soon")
        )
        unassigned = sum(1 for item in open_items if not item.get("assignee"))
        stale = sum(
            1
            for item in open_items
            if (self._days_since(item.get("changed"), today) or 0) >= 7
        )

        kpis = {
            "total": total,
            "open": open_count,
            "closed": closed_count,
            "completion_pct": completion_pct,
            "critical_open": critical_open,
            "high_open": high_open,
            "high_priority_open": critical_open + high_open,
            "in_review": in_review,
            "overdue": overdue,
            "at_risk": at_risk,
            "unassigned": unassigned,
            "stale": stale,
            "closed_this_week": len(recently_closed),
        }

        health = self._health_status(kpis)
        trends = self._activity_trends(items, recently_closed, week_ago, today)
        recommendations = self._recommendations(kpis, trends, open_items, items, today)

        executive_summary = self._executive_narrative(name, kpis, health, trends)
        detailed_summary = self._detailed_narrative(kpis, trends, open_items, total)
        tracker_items = self._tracker_item_rows(items, today, week_ago)
        filter_tabs = self._build_filter_tabs(tracker_items)

        return {
            "id": scope_id,
            "name": name,
            "path": path,
            "scope": scope,
            "item_count": total,
            "health": health,
            "headline": self._headline(name, kpis, health),
            "executive": {
                "summary": executive_summary,
                "health": health,
                "kpis": kpis,
                "state_chart": self._chart(open_items + closed_items, "state"),
                "priority_chart": self._priority_chart(open_items),
                "severity_chart": self._severity_chart(open_items),
            },
            "detailed": {
                "title": self.TRACKER_TITLE,
                "subtitle": self.TRACKER_SUBTITLE,
                "summary": detailed_summary,
                "kpis": {
                    "total_tracked": total,
                    "open": open_count,
                    "closed": closed_count,
                    "resolution_pct": completion_pct,
                    "critical_open": critical_open,
                    "high_open": high_open,
                    "in_review": in_review,
                    "closed_this_week": trends["items_closed_7d"],
                    "overdue_open": overdue,
                    "stale_open": stale,
                },
                "state_breakdown": self._state_breakdown(open_items + closed_items),
                "by_assignee": self._assignee_load(open_items),
                "open_items": self._open_item_rows(open_items, today),
                "tracker_items": tracker_items,
                "filter_tabs": filter_tabs,
            },
            "items": self._item_list(items, today, week_ago),
            "trends": trends,
            "recommendations": recommendations,
            "attention_items": self._attention_items(open_items, today),
            "wins": self._wins(recently_closed),
        }

    def _exclude_child_tasks(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [item for item in items if item.get("type") not in self.excluded_types]

    def _executive_narrative(
        self, name: str, kpis: dict[str, Any], health: str, trends: dict[str, Any]
    ) -> str:
        if kpis["total"] == 0:
            return f"No work items found in {name}. Verify scope filters or query criteria."

        health_word = {"red": "requires immediate attention", "amber": "needs monitoring", "green": "is on track"}
        lines = [
            f"{name} {health_word.get(health, 'needs review')}.",
            (
                f"{kpis['open']} of {kpis['total']} items remain open "
                f"({kpis['completion_pct']}% complete)."
            ),
        ]
        if kpis["high_priority_open"]:
            lines.append(
                f"{kpis['high_priority_open']} high-priority items still need resolution."
            )
        if trends["items_created_7d"] or trends["items_closed_7d"]:
            lines.append(trends["trend_summary"])
        if kpis["closed_this_week"]:
            lines.append(f"{kpis['closed_this_week']} items closed this week — maintain momentum.")
        return " ".join(lines)

    def _detailed_narrative(
        self,
        kpis: dict[str, Any],
        trends: dict[str, Any],
        open_items: list[dict],
        total: int,
    ) -> str:
        if total == 0:
            return "No items in scope (child tasks are excluded from this view)."

        open_count = kpis["open"]
        closed_count = kpis["closed"]
        pct = kpis["completion_pct"]

        parts = [f"{closed_count} of {total} items resolved ({pct}%)."]
        if open_count:
            detail_bits = []
            if kpis["critical_open"]:
                detail_bits.append(f"{kpis['critical_open']} critical priority")
            if kpis["high_open"]:
                detail_bits.append(f"{kpis['high_open']} high priority")
            if kpis["in_review"]:
                detail_bits.append(f"{kpis['in_review']} in PR review")
            open_line = f"{open_count} remain open"
            if detail_bits:
                open_line += f" ({', '.join(detail_bits)})"
            parts.append(open_line + ".")

        closed_7d = trends["items_closed_7d"]
        if closed_7d:
            parts.append(f"{closed_7d} closed in the last 7 days — good momentum.")
        elif open_count:
            parts.append("No closures in the last 7 days — consider a focused triage session.")

        if trends["items_created_7d"] > trends["items_closed_7d"]:
            parts.append(
                f"Intake ({trends['items_created_7d']}) exceeds closures "
                f"({trends['items_closed_7d']}) — backlog is growing."
            )
        return " ".join(parts)

    def _activity_trends(
        self,
        items: list[dict[str, Any]],
        recently_closed: list[dict[str, Any]],
        week_ago: date,
        today: date,
    ) -> dict[str, Any]:
        created_7d = sum(
            1
            for item in items
            if (created := self._parse_date(item.get("created"))) is not None
            and created >= week_ago
        )
        closed_7d = len(recently_closed)
        net = closed_7d - created_7d

        if created_7d > closed_7d:
            trend = "worsening"
            trend_summary = (
                f"Activity trend: {created_7d} created vs {closed_7d} closed in 7 days "
                f"(+{created_7d - closed_7d} net) — backlog growing."
            )
        elif closed_7d > created_7d:
            trend = "improving"
            trend_summary = (
                f"Activity trend: {closed_7d} closed vs {created_7d} created in 7 days "
                f"({closed_7d - created_7d} net reduction) — positive momentum."
            )
        else:
            trend = "stable"
            trend_summary = (
                f"Activity trend: {created_7d} created and {closed_7d} closed in 7 days — stable."
            )

        return {
            "items_created_7d": created_7d,
            "items_closed_7d": closed_7d,
            "defects_created_7d": created_7d,
            "defects_closed_7d": closed_7d,
            "net_change": net,
            "trend": trend,
            "trend_summary": trend_summary,
            "period_label": f"{week_ago.strftime('%b %d')} – {today.strftime('%b %d, %Y')}",
        }

    def _recommendations(
        self,
        kpis: dict[str, Any],
        trends: dict[str, Any],
        open_items: list[dict[str, Any]],
        items: list[dict[str, Any]],
        today: date,
    ) -> list[dict[str, Any]]:
        recs: list[dict[str, Any]] = []

        for insight in (
            self._sprint_velocity_risk(open_items, trends, today),
            self._assignee_blocker_rec(open_items, today),
            self._tag_triage_rec(items, today),
        ):
            if insight:
                recs.append(insight)

        overdue_items = [
            item for item in open_items if self._due_status(item, today) == "overdue"
        ]
        if kpis["overdue"]:
            recs.append(
                self._rec(
                    "high",
                    f"Escalate {kpis['overdue']} overdue item(s) in today's standup.",
                    "Overdue items block delivery commitments and erode stakeholder confidence.",
                    overdue_items,
                )
            )

        critical_open_items = [
            item for item in open_items if self._priority_rank(item) == 1
        ]
        if kpis["critical_open"] >= 3:
            recs.append(
                self._rec(
                    "high",
                    "Convene a 30-minute war room for critical open items.",
                    f"{kpis['critical_open']} critical items open — parallel resolution needed.",
                    critical_open_items,
                )
            )

        review_items = [
            item for item in open_items if item.get("state") == "PR Review"
        ]
        if kpis["in_review"]:
            recs.append(
                self._rec(
                    "high",
                    f"Clear PR review queue ({kpis['in_review']} item(s)) within 24 hours.",
                    "Items in review are dev-complete but not delivering value until merged.",
                    review_items,
                )
            )

        unassigned_items = [item for item in open_items if not item.get("assignee")]
        if kpis["unassigned"]:
            recs.append(
                self._rec(
                    "medium",
                    f"Assign owners to {kpis['unassigned']} unassigned open item(s).",
                    "Unowned work stalls — every open item needs a single accountable owner.",
                    unassigned_items,
                )
            )

        stale_items = [
            item
            for item in open_items
            if (self._days_since(item.get("changed"), today) or 0) >= 7
        ]
        if kpis["stale"]:
            recs.append(
                self._rec(
                    "medium",
                    f"Review {kpis['stale']} stale item(s) with no update in 7+ days.",
                    "Stale items may be blocked, deprioritized, or forgotten — confirm status or close.",
                    stale_items,
                )
            )

        if trends["trend"] == "worsening":
            burn_down_items = [
                item
                for item in open_items
                if self._priority_rank(item) <= 2
                or self._due_status(item, today) in ("overdue", "due_soon")
            ]
            recs.append(
                self._rec(
                    "high",
                    "Pause new feature work — dedicate capacity to backlog burn-down.",
                    trends["trend_summary"],
                    burn_down_items,
                )
            )
        elif trends["trend"] == "improving" and kpis["open"]:
            recs.append(
                self._rec(
                    "low",
                    f"Sustain current pace — {kpis['open']} items remain to close out the scope.",
                    "Closure rate exceeds intake; keep focus on remaining open items.",
                    open_items[:5],
                )
            )
        if not kpis["closed_this_week"] and kpis["open"]:
            recs.append(
                self._rec(
                    "medium",
                    "Set a weekly closure target (e.g. 3 items) for the team.",
                    "Zero closures in 7 days signals a throughput issue.",
                    sorted(open_items, key=self._item_sort_key)[:5],
                )
            )
        if not recs and kpis["open"] == 0:
            recs.append(
                self._rec(
                    "low",
                    "Scope complete — document lessons learned and close out the milestone.",
                    "All tracked items are resolved.",
                )
            )
        if not recs:
            recs.append(
                self._rec(
                    "low",
                    "Continue weekly triage — no critical blockers detected.",
                    "Overall health is manageable; maintain current cadence.",
                )
            )
        return recs[:8]

    def _rec(
        self,
        priority: str,
        action: str,
        rationale: str,
        items: list[dict[str, Any]] | None = None,
        *,
        limit: int = 8,
    ) -> dict[str, Any]:
        related = self._item_refs(items or [], limit=limit)
        return {
            "priority": priority,
            "action": action,
            "rationale": rationale,
            "related_items": related,
        }

    def _item_ref(self, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item.get("id"),
            "title": item.get("title", ""),
            "url": item.get("url", ""),
        }

    def _item_refs(
        self, items: list[dict[str, Any]], *, limit: int = 8
    ) -> list[dict[str, Any]]:
        return [
            self._item_ref(item)
            for item in sorted(items, key=self._item_sort_key)[:limit]
        ]

    def _sprint_velocity_risk(
        self,
        open_items: list[dict[str, Any]],
        trends: dict[str, Any],
        today: date,
    ) -> dict[str, Any] | None:
        if not open_items:
            return None

        velocity_per_week = trends["items_closed_7d"]
        if velocity_per_week <= 0:
            return None

        iterations = [item.get("iteration") for item in open_items if item.get("iteration")]
        if not iterations:
            return None

        milestone = max(set(iterations), key=iterations.count)
        milestone_short = milestone.rsplit("/", 1)[-1]

        open_count = len(open_items)
        days_to_clear = int((open_count / velocity_per_week) * 7)

        due_dates = [
            parsed
            for item in open_items
            if (parsed := self._parse_date(item.get("due_date"))) is not None
        ]
        days_until_milestone = (
            (min(due_dates) - today).days if due_dates else 14
        )

        if days_to_clear <= days_until_milestone:
            return None

        slip_days = days_to_clear - days_until_milestone
        p3_open = [item for item in open_items if self._priority_rank(item) == 3]
        descope_count = min(2, len(p3_open))
        if descope_count == 0:
            return None

        return self._rec(
            "high",
            (
                f"At current velocity, you'll miss the {milestone_short} milestone by "
                f"{slip_days} day{'s' if slip_days != 1 else ''} — consider descoping "
                f"{descope_count} P3 item{'s' if descope_count != 1 else ''}."
            ),
            (
                f"Closing {velocity_per_week} item(s)/week with {open_count} open "
                f"requires ~{days_to_clear} days; milestone pressure is "
                f"{max(days_until_milestone, 0)} days out."
            ),
            p3_open[:descope_count],
        )

    def _assignee_blocker_rec(
        self,
        open_items: list[dict[str, Any]],
        today: date,
        *,
        stale_threshold: int = 3,
        min_items: int = 4,
    ) -> dict[str, Any] | None:
        by_assignee: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in open_items:
            assignee = item.get("assignee")
            if assignee:
                by_assignee[assignee].append(item)

        for assignee, assigned_items in sorted(
            by_assignee.items(), key=lambda row: -len(row[1])
        ):
            if len(assigned_items) < min_items:
                continue
            stale_days = [
                self._days_since(item.get("changed"), today) or 0
                for item in assigned_items
            ]
            if min(stale_days) >= stale_threshold:
                return self._rec(
                    "high",
                    (
                        f"{assignee} has {len(assigned_items)} items assigned but "
                        f"hasn't updated any in {stale_threshold}+ days — potential blocker."
                    ),
                    (
                        "Assignee may be blocked, context-switching, or needs "
                        "unblocking in standup."
                    ),
                    assigned_items,
                )
        return None

    def _tag_triage_rec(
        self, items: list[dict[str, Any]], today: date
    ) -> dict[str, Any] | None:
        tag_label = "customer-reported"
        tagged_closed: list[int] = []
        untagged_closed: list[int] = []

        for item in items:
            if item.get("state") not in self.closed_states:
                continue
            resolution_days = self._resolution_days(item)
            if resolution_days is None:
                continue
            if self._has_tag(item, tag_label):
                tagged_closed.append(resolution_days)
            else:
                untagged_closed.append(resolution_days)

        if len(tagged_closed) < 2 or not untagged_closed:
            return None

        tagged_avg = sum(tagged_closed) / len(tagged_closed)
        untagged_avg = sum(untagged_closed) / len(untagged_closed)
        if untagged_avg <= 0:
            return None

        ratio = tagged_avg / untagged_avg
        if ratio < 2:
            return None

        tagged_items = [item for item in items if self._has_tag(item, tag_label)]
        return self._rec(
            "medium",
            (
                f"Items tagged '{tag_label}' have {ratio:.1f}x longer resolution time "
                "— consider a dedicated triage."
            ),
            (
                f"Customer-reported items average {tagged_avg:.0f} days to close vs "
                f"{untagged_avg:.0f} days for other items."
            ),
            tagged_items,
        )

    def _item_categories(
        self, item: dict[str, Any], today: date, week_ago: date
    ) -> list[str]:
        categories = [f"state:{item.get('state', 'Unknown')}"]
        is_open = item.get("state") not in self.closed_states

        if is_open:
            due_status = self._due_status(item, today)
            if due_status == "overdue":
                categories.append("overdue")
            if (
                self._priority_rank(item) <= 2
                and due_status in ("overdue", "due_soon")
            ):
                categories.append("at-risk")
            if (self._days_since(item.get("changed"), today) or 0) >= 7:
                categories.append("stale")
            if not item.get("assignee"):
                categories.append("unassigned")
            if self._priority_rank(item) == 1:
                categories.append("critical")
            if self._priority_rank(item) == 2:
                categories.append("high-priority")
        else:
            changed = self._parse_date(item.get("changed"))
            if changed is not None and changed >= week_ago:
                categories.append("closed-this-week")

        if self._has_tag(item, "customer-reported"):
            categories.append("customer-reported")

        return categories

    def _tracker_item_rows(
        self, items: list[dict[str, Any]], today: date, week_ago: date
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for item in sorted(items, key=self._item_sort_key):
            is_open = item.get("state") not in self.closed_states
            row: dict[str, Any] = {
                "id": item.get("id"),
                "title": item.get("title", ""),
                "type": item.get("type", ""),
                "state": item.get("state", ""),
                "assignee": item.get("assignee") or "Unassigned",
                "priority": self._format_priority_display(item),
                "severity": self._format_severity_display(item),
                "due_date": self._format_date(item.get("due_date")),
                "created_date": self._format_date(item.get("created")),
                "url": item.get("url", ""),
                "categories": self._item_categories(item, today, week_ago),
            }
            if is_open:
                row["days_open"] = self._days_since(item.get("created"), today)
                row["days_since_update"] = self._days_since(item.get("changed"), today)
                row["due_status"] = self._due_status(item, today)
            else:
                row["days_open"] = self._days_since(item.get("created"), today)
                row["days_since_update"] = self._days_since(item.get("changed"), today)
                row["due_status"] = "none"
            rows.append(row)
        return rows

    def _build_filter_tabs(
        self, tracker_items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        tabs: list[dict[str, Any]] = [
            {
                "key": "all",
                "label": "All",
                "count": len(tracker_items),
                "group": "all",
            }
        ]
        state_counts: dict[str, int] = defaultdict(int)
        insight_counts: dict[str, int] = defaultdict(int)

        for row in tracker_items:
            for category in row.get("categories", []):
                if category.startswith("state:"):
                    state_counts[category[6:]] += 1
                else:
                    insight_counts[category] += 1

        seen_states: set[str] = set()
        for state in STATE_TAB_ORDER:
            if state in state_counts:
                tabs.append(
                    {
                        "key": f"state:{state}",
                        "label": state,
                        "count": state_counts[state],
                        "group": "state",
                    }
                )
                seen_states.add(state)
        for state in sorted(state_counts):
            if state not in seen_states:
                tabs.append(
                    {
                        "key": f"state:{state}",
                        "label": state,
                        "count": state_counts[state],
                        "group": "state",
                    }
                )

        for key, label in INSIGHT_TAB_ORDER:
            count = insight_counts.get(key, 0)
            if count > 0:
                tabs.append(
                    {
                        "key": key,
                        "label": label,
                        "count": count,
                        "group": "insight",
                    }
                )

        return tabs

    @staticmethod
    def _parse_tags(item: dict[str, Any]) -> list[str]:
        tags_raw = item.get("tags") or ""
        if isinstance(tags_raw, list):
            return [tag.strip() for tag in tags_raw if tag.strip()]
        return [tag.strip() for tag in str(tags_raw).split(";") if tag.strip()]

    def _has_tag(self, item: dict[str, Any], tag_label: str) -> bool:
        needle = tag_label.lower()
        return any(needle in tag.lower() for tag in self._parse_tags(item))

    def _resolution_days(self, item: dict[str, Any]) -> int | None:
        created = self._parse_date(item.get("created"))
        changed = self._parse_date(item.get("changed"))
        if created is None or changed is None:
            return None
        return max((changed - created).days, 0)

    def _state_breakdown(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            counts[item.get("state", "Unknown")] += 1
        return [
            {
                "state": state,
                "count": count,
                "is_open": state not in self.closed_states,
            }
            for state, count in sorted(
                counts.items(),
                key=lambda row: (row[0] in self.closed_states, -row[1], row[0]),
            )
        ]

    def _open_item_rows(
        self, open_items: list[dict[str, Any]], today: date
    ) -> list[dict[str, Any]]:
        rows = []
        for item in sorted(open_items, key=self._item_sort_key):
            rows.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "state": item.get("state", ""),
                    "assignee": item.get("assignee") or "Unassigned",
                    "priority": self._format_priority_display(item),
                    "severity": self._format_severity_display(item),
                    "due_date": self._format_date(item.get("due_date")),
                    "days_open": self._days_since(item.get("created"), today),
                    "days_since_update": self._days_since(item.get("changed"), today),
                    "due_status": self._due_status(item, today),
                    "url": item.get("url", ""),
                }
            )
        return rows

    def _item_list(
        self,
        items: list[dict[str, Any]],
        today: date,
        week_ago: date,
    ) -> list[dict[str, Any]]:
        rows = []
        for item in sorted(items, key=self._item_sort_key):
            rows.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "type": item.get("type", ""),
                    "state": item.get("state", ""),
                    "assignee": item.get("assignee") or "Unassigned",
                    "priority": self._format_priority_display(item),
                    "severity": self._format_severity_display(item),
                    "due_date": self._format_date(item.get("due_date")),
                    "is_open": item.get("state") not in self.closed_states,
                    "url": item.get("url", ""),
                    "categories": self._item_categories(item, today, week_ago),
                }
            )
        return rows

    def _attention_items(
        self, open_items: list[dict[str, Any]], today: date
    ) -> list[dict[str, Any]]:
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in open_items:
            score = 0
            priority = self._priority_rank(item)
            due_status = self._due_status(item, today)
            days_stale = self._days_since(item.get("changed"), today) or 0
            if due_status == "overdue":
                score += 100
            elif due_status == "due_soon":
                score += 60
            if priority == 1:
                score += 40
            elif priority == 2:
                score += 20
            if not item.get("assignee"):
                score += 15
            if days_stale >= 7:
                score += 10
            if score == 0:
                continue
            reasons = []
            if due_status == "overdue":
                reasons.append("Overdue")
            elif due_status == "due_soon":
                reasons.append("Due soon")
            if priority <= 2:
                reasons.append(PRIORITY_LABELS.get(priority, "High priority"))
            if not item.get("assignee"):
                reasons.append("Unassigned")
            if days_stale >= 7:
                reasons.append("Stale")
            scored.append(
                (
                    -score,
                    {
                        "id": item.get("id"),
                        "title": item.get("title", ""),
                        "state": item.get("state", ""),
                        "assignee": item.get("assignee") or "Unassigned",
                        "priority": self._format_priority_display(item),
                        "severity": self._format_severity_display(item),
                        "due_date": self._format_date(item.get("due_date")),
                        "url": item.get("url", ""),
                        "reason": ", ".join(reasons),
                    },
                )
            )
        scored.sort(key=lambda row: (row[0], self._item_sort_key_from_row(row[1])))
        return [item for _, item in scored[:5]]

    def _wins(self, recently_closed: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items = sorted(recently_closed, key=self._item_sort_key)
        wins = []
        for item in items[:5]:
            wins.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title", ""),
                    "priority": self._format_priority_display(item),
                    "severity": self._format_severity_display(item),
                    "closed": self._format_date(item.get("changed")),
                    "assignee": item.get("assignee") or "Unassigned",
                    "url": item.get("url", ""),
                }
            )
        return wins

    def _assignee_load(self, open_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[str, int] = defaultdict(int)
        for item in open_items:
            counts[item.get("assignee") or "Unassigned"] += 1
        return [
            {"assignee": assignee, "open": count}
            for assignee, count in sorted(counts.items(), key=lambda row: (-row[1], row[0]))
        ]

    def _chart(self, items: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            counts[item.get(field) or "Unknown"] += 1
        return [
            {"label": label, "count": count}
            for label, count in sorted(counts.items(), key=lambda row: -row[1])
        ]

    def _priority_chart(self, open_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[int, int] = defaultdict(int)
        for item in open_items:
            rank = self._priority_rank(item)
            if rank in PRIORITY_ORDER:
                counts[rank] += 1
        return [
            {"label": str(rank), "count": counts.get(rank, 0)}
            for rank in PRIORITY_ORDER
        ]

    def _severity_chart(self, open_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        counts: dict[str, int] = defaultdict(int)
        for item in open_items:
            label = self._format_severity_display(item)
            if label in SEVERITY_RANK:
                counts[label] += 1
        return [
            {"label": label, "count": counts.get(label, 0)}
            for label in SEVERITY_ORDER
        ]

    def _health_status(self, kpis: dict[str, Any]) -> str:
        if kpis["overdue"] > 0 or kpis["critical_open"] >= 3:
            return "red"
        if kpis["at_risk"] > 0 or kpis["stale"] > 0 or kpis["unassigned"] > 2:
            return "amber"
        if kpis["open"] == 0 and kpis["total"] > 0:
            return "green"
        if kpis["completion_pct"] >= 70 and kpis["high_priority_open"] == 0:
            return "green"
        return "amber" if kpis["open"] > 0 else "green"

    def _headline(self, name: str, kpis: dict[str, Any], health: str) -> str:
        if kpis["total"] == 0:
            return f"{name}: no items in scope."
        parts = [
            f"{kpis['open']} open of {kpis['total']} items ({kpis['completion_pct']}% complete)."
        ]
        if kpis["high_priority_open"]:
            parts.append(f"{kpis['high_priority_open']} high-priority still open.")
        if kpis["closed_this_week"]:
            parts.append(f"{kpis['closed_this_week']} closed this week.")
        if kpis["overdue"]:
            parts.append(f"{kpis['overdue']} overdue — needs attention.")
        elif health == "green" and kpis["open"] == 0:
            parts.append("All items complete.")
        elif health == "green":
            parts.append("On track.")
        return " ".join(parts)

    def _item_sort_key(self, item: dict[str, Any]) -> tuple[int, int, int]:
        return (
            self._priority_rank(item),
            self._severity_rank(item),
            int(item.get("id") or 0),
        )

    def _item_sort_key_from_row(self, row: dict[str, Any]) -> tuple[int, int]:
        priority = row.get("priority")
        severity = row.get("severity")
        try:
            priority_rank = int(priority) if priority not in (None, "—") else 99
        except (TypeError, ValueError):
            priority_rank = 99
        severity_rank = SEVERITY_RANK.get(severity, 99) if severity not in (None, "—") else 99
        return (priority_rank, severity_rank)

    @staticmethod
    def _priority_rank(item: dict[str, Any]) -> int:
        priority = item.get("priority")
        if priority is None:
            return 99
        try:
            value = int(priority)
            return value if value in PRIORITY_ORDER else 99
        except (TypeError, ValueError):
            return 99

    def _severity_rank(self, item: dict[str, Any]) -> int:
        label = self._format_severity_display(item)
        if label == "—":
            return 99
        return SEVERITY_RANK.get(label, 99)

    @staticmethod
    def _parse_date(value: Any) -> date | None:
        if not value:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                return None
        return None

    def _days_since(self, value: Any, today: date) -> int | None:
        parsed = self._parse_date(value)
        return (today - parsed).days if parsed else None

    def _due_status(self, item: dict[str, Any], today: date) -> str:
        due = self._parse_date(item.get("due_date"))
        if due is None:
            return "none"
        if due < today:
            return "overdue"
        if due <= today + timedelta(days=3):
            return "due_soon"
        return "on_track"

    @staticmethod
    def _format_priority_display(item: dict[str, Any]) -> str:
        priority = item.get("priority")
        if priority is None:
            return "—"
        try:
            return str(int(priority))
        except (TypeError, ValueError):
            return str(priority)

    @staticmethod
    def _format_severity_display(item: dict[str, Any]) -> str:
        severity = item.get("severity")
        if not severity:
            return "—"
        if isinstance(severity, str) and " - " in severity:
            return severity.split(" - ", 1)[1].strip()
        return str(severity)

    @staticmethod
    def _format_date(value: Any) -> str:
        if not value:
            return "—"
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                return parsed.strftime("%b %d, %Y")
            except ValueError:
                return "—"
        if isinstance(value, datetime):
            return value.strftime("%b %d, %Y")
        if isinstance(value, date):
            return value.strftime("%b %d, %Y")
        return "—"
