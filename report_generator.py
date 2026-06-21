from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Template


@dataclass
class ReportData:
    generated_at: datetime
    project: str
    area_path: str | None
    area_analysis: dict[str, Any] | None
    queries: list[dict[str, Any]]
    query_analyses: dict[str, dict[str, Any]]
    default_query_id: str
    show_narrative_footer: bool = False


class ReportGenerator:
    def build(
        self,
        project: str,
        area_path: str | None,
        area_analysis: dict[str, Any] | None,
        queries: list[dict[str, Any]],
        query_analyses: dict[str, dict[str, Any]],
        default_query_id: str,
        show_narrative_footer: bool = False,
    ) -> ReportData:
        return ReportData(
            generated_at=datetime.now(timezone.utc),
            project=project,
            area_path=area_path,
            area_analysis=area_analysis,
            queries=queries,
            query_analyses=query_analyses,
            default_query_id=default_query_id,
            show_narrative_footer=show_narrative_footer,
        )

    def render_html(self, data: ReportData) -> str:
        template = Template(HTML_TEMPLATE)
        return template.render(
            data=data,
            area_json=json.dumps(data.area_analysis) if data.area_analysis else "null",
            analyses_json=json.dumps(data.query_analyses),
            generated_label=data.generated_at.astimezone().strftime("%b %d, %Y %I:%M %p %Z"),
        )

    def save_report(self, data: ReportData, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = data.generated_at.strftime("%Y-%m-%d")
        html_path = output_dir / f"daily-report-{stamp}.html"
        html_path.write_text(self.render_html(data), encoding="utf-8")
        return html_path


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Leadership Dashboard — {{ data.project }}</title>
  <style>
    :root {
      --bg: #f4f6f8;
      --surface: #ffffff;
      --surface-dark: #1a2332;
      --surface2: #f9fafb;
      --text: #1f2937;
      --text-light: #f3f4f6;
      --muted: #6b7280;
      --accent: #0078d4;
      --danger: #d13438;
      --warning: #ca5010;
      --success: #107c10;
      --border: #e5e7eb;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; }
    .app-header {
      background: var(--surface);
      border-bottom: 1px solid var(--border);
      padding: 16px 24px;
      display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
    }
    .app-header h1 { font-size: 18px; font-weight: 600; }
    .app-header p { font-size: 12px; color: var(--muted); }
    .top-tabs { display: flex; gap: 4px; background: var(--surface2); padding: 4px; border-radius: 10px; }
    .top-tab {
      padding: 8px 18px; border: none; border-radius: 8px; background: transparent;
      font-size: 14px; font-weight: 500; cursor: pointer; color: var(--muted);
    }
    .top-tab.active { background: var(--surface); color: var(--accent); box-shadow: 0 1px 3px rgba(0,0,0,.08); }
    .layout { display: flex; min-height: calc(100vh - 65px); }
    .sidebar {
      width: 270px; background: var(--surface); border-right: 1px solid var(--border);
      display: none; flex-direction: column; flex-shrink: 0;
    }
    .sidebar.visible { display: flex; }
    .sidebar-header { padding: 16px; border-bottom: 1px solid var(--border); font-size: 13px; font-weight: 600; }
    .search {
      margin: 12px 16px; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border);
      font-size: 13px; width: calc(100% - 32px);
    }
    .query-list { flex: 1; overflow-y: auto; padding: 8px; }
    .query-btn {
      display: block; width: 100%; text-align: left; padding: 10px 12px; margin-bottom: 4px;
      border: none; border-radius: 8px; background: transparent; cursor: pointer; font-size: 13px;
    }
    .query-btn:hover { background: var(--surface2); }
    .query-btn.active { background: #eef6fc; border-left: 3px solid var(--accent); }
    .query-btn .name { font-weight: 500; display: block; }
    .query-btn .meta { font-size: 11px; color: var(--muted); margin-top: 2px; }
    .health-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
    .health-dot.red { background: var(--danger); }
    .health-dot.amber { background: var(--warning); }
    .health-dot.green { background: var(--success); }
    .main { flex: 1; overflow-y: auto; padding: 24px 28px; }
    .scope-title { font-size: 20px; font-weight: 600; margin-bottom: 4px; }
    .scope-sub { font-size: 13px; color: var(--muted); margin-bottom: 20px; }
    .health-badge {
      display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 11px;
      font-weight: 600; text-transform: uppercase; margin-left: 8px; vertical-align: middle;
    }
    .health-badge.red { background: #fde7e9; color: var(--danger); }
    .health-badge.amber { background: #fff4ce; color: var(--warning); }
    .health-badge.green { background: #dff6dd; color: var(--success); }

    /* Expandable cards */
    .expand-card {
      background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
      margin-bottom: 16px; overflow: hidden;
    }
    .expand-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 14px 18px; cursor: pointer; user-select: none; background: var(--surface);
    }
    .expand-header:hover { background: var(--surface2); }
    .expand-header h2 { font-size: 16px; font-weight: 600; }
    .expand-header .chevron { font-size: 18px; color: var(--muted); transition: transform .2s; }
    .expand-card.open .chevron { transform: rotate(180deg); }
    .expand-body { display: none; padding: 0 18px 18px; }
    .expand-card.open .expand-body { display: block; }

    /* Executive summary — dark inner panel (Image 1) */
    .exec-panel {
      background: var(--surface-dark); color: var(--text-light); border-radius: 10px; padding: 20px;
    }
    .exec-panel .headline { font-size: 15px; color: #d1d5db; margin-bottom: 16px; line-height: 1.6; }
    .exec-panel .exec-summary-box {
      background: rgba(59,158,255,0.12); border-radius: 8px; padding: 12px 14px;
      font-size: 14px; margin-bottom: 18px; line-height: 1.6;
    }
    .exec-panel .progress-label { font-size: 12px; color: #9ca3af; margin-bottom: 6px; }
    .exec-panel .progress-track { height: 10px; background: #374151; border-radius: 999px; overflow: hidden; margin-bottom: 18px; }
    .exec-panel .progress-fill { height: 100%; background: var(--success); border-radius: 999px; }
    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 18px; }
    .kpi { background: rgba(255,255,255,0.05); border: 1px solid #374151; border-radius: 8px; padding: 12px; }
    .exec-panel .kpi { background: rgba(255,255,255,0.05); border-color: #374151; }
    .kpi-value { font-size: 24px; font-weight: 700; }
    .kpi-label { font-size: 11px; color: var(--muted); margin-top: 2px; }
    .exec-panel .kpi-label { color: #9ca3af; }
    .kpi-value.danger { color: #f87171; }
    .kpi-value.warning { color: #fbbf24; }
    .kpi-value.success { color: #4ade80; }
    .panels { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    @media (max-width: 800px) { .panels { grid-template-columns: 1fr; } }
    .panel { background: rgba(255,255,255,0.05); border: 1px solid #374151; border-radius: 8px; padding: 14px; }
    .panel h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #9ca3af; margin-bottom: 12px; }
    .bar-row { margin-bottom: 8px; }
    .bar-label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px; }
    .bar-track { height: 6px; background: #374151; border-radius: 999px; overflow: hidden; }
    .bar-fill { height: 100%; background: var(--accent); border-radius: 999px; }

    /* Detailed view — light panel (Image 2) */
    .detail-panel { border-left: 4px solid var(--accent); padding: 4px 0; }
    .detail-panel h3 { font-size: 17px; color: var(--accent); margin-bottom: 4px; }
    .detail-panel .sub { font-size: 13px; color: var(--muted); margin-bottom: 14px; }
    .detail-panel .narrative {
      background: #f0f7ff; border-radius: 8px; padding: 12px 14px; font-size: 14px;
      margin-bottom: 16px; line-height: 1.6;
    }
    .detail-panel .kpi { background: var(--surface); border: 1px solid var(--border); }
    .detail-panel .progress-track { height: 10px; background: #e5e7eb; border-radius: 999px; overflow: hidden; margin: 8px 0 16px; }
    .detail-panel .progress-fill { height: 100%; background: var(--success); border-radius: 999px; }
    .state-filter-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    .state-tab {
      padding: 6px 14px; border-radius: 999px; font-size: 12px; font-weight: 500;
      border: 1px solid var(--border); background: var(--surface); color: var(--text);
      cursor: pointer; transition: background .15s, border-color .15s;
    }
    .state-tab:hover { background: var(--surface2); }
    .state-tab.active { background: #eef6fc; border-color: var(--accent); color: var(--accent); font-weight: 600; }
    .state-tab.open-state { background: #fffdf5; }
    .state-tab.open-state.active { background: #fff4ce; border-color: #ca5010; color: #8a4b00; }
    .state-tab.closed-state { background: #f6fff6; }
    .state-tab.closed-state.active { background: #e8f5e9; border-color: var(--success); color: var(--success); }
    .state-tab.insight-tab { background: #f5f3ff; }
    .state-tab.insight-tab.active { background: #ede9fe; border-color: #7c3aed; color: #5b21b6; }
    .filter-count { color: var(--muted); font-size: 11px; margin-bottom: 8px; }
    .filter-hint { color: var(--muted); font-size: 11px; margin-bottom: 6px; }
    .assignee-line { font-size: 13px; color: var(--muted); margin-bottom: 14px; }
    .table-controls { margin-bottom: 14px; }
    .control-row {
      display: flex; flex-wrap: wrap; align-items: flex-end; gap: 12px;
      margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);
    }
    .assignee-filter { position: relative; min-width: 200px; }
    .assignee-filter-btn {
      width: 100%; text-align: left; padding: 8px 12px; border-radius: 8px;
      border: 1px solid var(--border); background: var(--surface); font-size: 13px; cursor: pointer;
    }
    .assignee-filter-btn:hover { background: var(--surface2); }
    .assignee-menu {
      display: none; position: absolute; z-index: 20; top: calc(100% + 4px); left: 0; right: 0;
      max-height: 220px; overflow-y: auto; background: var(--surface); border: 1px solid var(--border);
      border-radius: 8px; padding: 8px; box-shadow: 0 4px 12px rgba(0,0,0,.1);
    }
    .assignee-menu.open { display: block; }
    .assignee-option {
      display: flex; align-items: center; gap: 8px; padding: 6px 8px; font-size: 13px;
      border-radius: 6px; cursor: pointer;
    }
    .assignee-option:hover { background: var(--surface2); }
    .assignee-option.assignee-all { border-bottom: 1px solid var(--border); margin-bottom: 4px; padding-bottom: 8px; }
    .sort-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 13px; }
    .sort-controls select {
      padding: 7px 10px; border-radius: 8px; border: 1px solid var(--border);
      background: var(--surface); font-size: 13px;
    }
    .clear-filters-btn {
      padding: 8px 14px; border-radius: 8px; border: 1px solid var(--border);
      background: var(--surface2); font-size: 12px; cursor: pointer;
    }
    .clear-filters-btn:hover { background: var(--border); }

    /* Tables */
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }
    th { background: var(--surface2); font-weight: 600; font-size: 12px; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; background: #eef2ff; color: #3730a3; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .due-overdue { color: var(--danger); font-weight: 600; }
    .due-soon { color: var(--warning); font-weight: 600; }

    /* Trends + recommendations */
    .trend-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 14px; }
    .trend-card { background: var(--surface2); border-radius: 8px; padding: 14px; text-align: center; }
    .trend-card .val { font-size: 28px; font-weight: 700; }
    .trend-card .lbl { font-size: 12px; color: var(--muted); }
    .trend-card.improving .val { color: var(--success); }
    .trend-card.worsening .val { color: var(--danger); }
    .trend-summary { font-size: 14px; padding: 12px; background: var(--surface2); border-radius: 8px; margin-bottom: 14px; }
    .rec-list { list-style: none; }
    .rec-list li {
      padding: 12px 14px; border: 1px solid var(--border); border-radius: 8px;
      margin-bottom: 8px; font-size: 13px;
    }
    .rec-list li strong { display: block; margin-bottom: 4px; }
    .rec-priority {
      display: inline-block; font-size: 10px; font-weight: 700; text-transform: uppercase;
      padding: 2px 6px; border-radius: 4px; margin-right: 6px;
    }
    .rec-priority.high { background: #fde7e9; color: var(--danger); }
    .rec-priority.medium { background: #fff4ce; color: var(--warning); }
    .rec-priority.low { background: #dff6dd; color: var(--success); }
    .rec-rationale { color: var(--muted); font-size: 12px; margin-top: 4px; }
    .rec-items { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
    .rec-items a { font-size: 12px; }
    .section-title { font-size: 15px; font-weight: 600; margin: 20px 0 12px; }
    .empty { color: var(--muted); font-style: italic; font-size: 13px; }
    .hidden { display: none !important; }

    /* Narrative footer (demo / presentation mode) */
    .narrative-footer {
      margin: 32px 28px 40px; padding: 24px 28px; background: var(--surface);
      border: 1px solid var(--border); border-radius: 12px;
      border-left: 4px solid var(--accent);
    }
    .narrative-footer blockquote {
      font-size: 15px; font-style: italic; color: var(--text); line-height: 1.7;
      margin: 0 0 20px; padding: 0;
    }
    .narrative-footer .narrative-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;
    }
    .narrative-footer .narrative-card {
      background: var(--surface2); border-radius: 8px; padding: 14px 16px; font-size: 13px; line-height: 1.6;
    }
    .narrative-footer .narrative-card strong {
      display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .04em;
      color: var(--muted); margin-bottom: 6px;
    }
    .narrative-footer .impact-highlight {
      background: #eef6fc; border: 1px solid #b3d7f2; border-radius: 8px;
      padding: 14px 16px; font-size: 14px; margin-bottom: 16px; line-height: 1.6;
    }
    .narrative-footer .v2-tease {
      margin-top: 16px; font-size: 13px; color: var(--accent); font-weight: 500;
    }
  </style>
</head>
<body>
  <header class="app-header">
    <div>
      <h1>{{ data.project }} — Leadership Dashboard</h1>
      <p>Generated {{ generated_label }}</p>
    </div>
    <div class="top-tabs">
      <button class="top-tab active" data-tab="area">Area Path Report</button>
      <button class="top-tab" data-tab="queries">Shared Queries Report</button>
    </div>
  </header>

  <div class="layout">
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-header">Shared Queries</div>
      <input type="search" class="search" id="query-search" placeholder="Filter queries…" />
      <nav class="query-list" id="query-list">
        {% for q in data.queries %}
        <button class="query-btn{% if q.id == data.default_query_id %} active{% endif %}"
                data-id="{{ q.id }}" data-name="{{ q.name }}">
          <span class="name"><span class="health-dot {{ q.health }}"></span>{{ q.name }}</span>
          <span class="meta">{{ q.item_count }} items</span>
        </button>
        {% endfor %}
      </nav>
    </aside>

    <main class="main">
      <div id="area-view">
        <div class="scope-title" id="area-title">Area Path Report</div>
        <div class="scope-sub" id="area-sub"></div>
        <div id="area-content"></div>
      </div>
      <div id="query-view" class="hidden">
        <div class="scope-title" id="query-title">Shared Query Report</div>
        <div class="scope-sub" id="query-sub"></div>
        <div id="query-content"></div>
      </div>
    </main>
  </div>

  {% if data.show_narrative_footer %}
  <footer class="narrative-footer">
    <blockquote>
      "I didn't build this because I love building tools. I built it because I was tired of
      spending more time reporting on progress than actually driving it."
    </blockquote>
    <div class="impact-highlight">
      <strong>Measurable impact (projected)</strong>
      If this saves 15 min per stand-up × 5 stand-ups/week × 4 teams, that's
      <strong>5 hours/week</strong> of engineering time returned to building.
    </div>
    <div class="narrative-grid">
      <div class="narrative-card">
        <strong>Power BI vs. this</strong>
        Yes, Power BI exists. It shows you data. This tells you what to do about it.
      </div>
      <div class="narrative-card">
        <strong>Why the barrier collapsed</strong>
        The point isn't that this was built in 2 hours. The point is that the barrier to PMs
        creating their own decision-support tools has collapsed.
      </div>
      <div class="narrative-card">
        <strong>Decision support, not dashboards</strong>
        PM recommendations surface sprint risk, assignee blockers, and tag-based triage gaps —
        actionable next steps, not another chart to interpret.
      </div>
    </div>
    <p class="v2-tease">Next: predictive sprint risk scoring and automated escalation triggers.</p>
  </footer>
  {% endif %}

  <script>
    const areaAnalysis = {{ area_json | safe }};
    const queryAnalyses = {{ analyses_json | safe }};
    const defaultQueryId = "{{ data.default_query_id }}";
    let activeTab = "area";
    let activeQueryId = defaultQueryId;

    function esc(s) {
      const d = document.createElement("div");
      d.textContent = s;
      return d.innerHTML;
    }

    function renderBars(items, maxOverride) {
      if (!items || !items.length) return '<p class="empty">No data</p>';
      const max = maxOverride || Math.max(...items.map(r => r.count), 1);
      return items.map(row => {
        const pct = Math.round((row.count / max) * 100);
        return `<div class="bar-row">
          <div class="bar-label"><span>${esc(row.label)}</span><span>${row.count}</span></div>
          <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
        </div>`;
      }).join("");
    }

    const SEVERITY_RANK = { "Critical": 1, "High": 2, "Medium": 3, "Low": 4 };

    function categoryAttr(categories) {
      return (categories || []).join("|");
    }

    function priorityRank(priority) {
      const value = parseInt(priority, 10);
      return Number.isFinite(value) ? value : 99;
    }

    function severityRank(severity) {
      return SEVERITY_RANK[severity] || 99;
    }

    function dueSortKey(dueDate) {
      if (!dueDate || dueDate === "—") return Number.MAX_SAFE_INTEGER;
      const parsed = Date.parse(dueDate);
      return Number.isFinite(parsed) ? parsed : Number.MAX_SAFE_INTEGER;
    }

    function rowDataAttrs(item) {
      const assignee = item.assignee || "Unassigned";
      return `data-categories="${esc(categoryAttr(item.categories))}" data-id="${item.id}" data-priority-rank="${priorityRank(item.priority)}" data-severity-rank="${severityRank(item.severity)}" data-state="${esc(item.state)}" data-assignee="${esc(assignee)}" data-due-sort="${dueSortKey(item.due_date)}"`;
    }

    function tabClass(tab) {
      if (tab.group === "insight") return "insight-tab";
      if (tab.group === "state") {
        const closedStates = ["Closed", "Done", "Resolved", "Removed"];
        return closedStates.includes(tab.label) ? "closed-state" : "open-state";
      }
      return "";
    }

    function buildTableControls(filterTabs, items, targetId, controlsId) {
      const assignees = [...new Set(items.map(item => item.assignee || "Unassigned"))].sort();
      const tabs = (filterTabs || []).map(tab => {
        const cls = tabClass(tab);
        const active = tab.key === "all" ? " active" : "";
        return `<button type="button" class="state-tab${cls ? " " + cls : ""}${active}" data-filter="${esc(tab.key)}">${esc(tab.label)} (${tab.count})</button>`;
      }).join("");
      const assigneeOptions = assignees.map(name =>
        `<label class="assignee-option"><input type="checkbox" value="${esc(name)}" checked> ${esc(name)}</label>`
      ).join("");
      return `
        <div class="table-controls" id="${controlsId}" data-target="${targetId}">
          <div class="filter-hint">Category filters — select multiple (matches any selected)</div>
          <div class="state-filter-bar">${tabs}</div>
          <div class="control-row">
            <div class="assignee-filter">
              <button type="button" class="assignee-filter-btn" aria-expanded="false">Assignees: All</button>
              <div class="assignee-menu">
                <label class="assignee-option assignee-all">
                  <input type="checkbox" value="__all__" checked> <strong>All assignees</strong>
                </label>
                ${assigneeOptions}
              </div>
            </div>
            <div class="sort-controls">
              <label>Sort
                <select class="sort-primary">
                  <option value="priority" selected>Priority</option>
                  <option value="severity">Severity</option>
                  <option value="state">State</option>
                  <option value="assignee">Assignee</option>
                  <option value="due">Due date</option>
                  <option value="id">ID</option>
                </select>
              </label>
              <label>then
                <select class="sort-secondary">
                  <option value="severity" selected>Severity</option>
                  <option value="priority">Priority</option>
                  <option value="none">None</option>
                  <option value="state">State</option>
                  <option value="assignee">Assignee</option>
                  <option value="due">Due date</option>
                  <option value="id">ID</option>
                </select>
              </label>
            </div>
            <button type="button" class="clear-filters-btn">Clear filters</button>
          </div>
          <div class="filter-count"></div>
        </div>`;
    }

    function renderDetailRow(item) {
      const dueClass = item.due_status === "overdue" ? "due-overdue"
        : item.due_status === "due_soon" ? "due-soon" : "";
      return `<tr ${rowDataAttrs(item)}>
        <td><a href="${item.url}" target="_blank">#${item.id}</a></td>
        <td>${esc(item.title)}</td>
        <td>${esc(item.type)}</td>
        <td>${esc(item.priority)}</td>
        <td>${esc(item.severity)}</td>
        <td>${esc(item.state)}</td>
        <td>${esc(item.assignee)}</td>
        <td class="${dueClass}">${esc(item.due_date)}</td>
        <td>${esc(item.created_date)}</td>
        <td>${item.days_open != null ? item.days_open + "d" : "—"}</td>
        <td>${item.days_since_update != null ? item.days_since_update + "d ago" : "—"}</td>
      </tr>`;
    }

    function renderAllItemRow(item) {
      return `<tr ${rowDataAttrs(item)}>
        <td><a href="${item.url}" target="_blank">#${item.id}</a></td>
        <td>${esc(item.title)}</td>
        <td>${esc(item.type)}</td>
        <td>${esc(item.state)}</td>
        <td>${esc(item.priority)}</td>
        <td>${esc(item.severity)}</td>
        <td>${esc(item.assignee)}</td>
        <td>${esc(item.due_date)}</td>
      </tr>`;
    }

    function renderRecLinks(items) {
      if (!items || !items.length) return "";
      const links = items.map(item =>
        `<a href="${item.url}" target="_blank" rel="noopener">#${item.id} — ${esc(item.title)}</a>`
      ).join("");
      return `<div class="rec-items"><strong style="font-size:11px;color:var(--muted)">Related work items:</strong>${links}</div>`;
    }

    function getSortValue(row, key) {
      if (key === "priority") return parseInt(row.dataset.priorityRank, 10) || 99;
      if (key === "severity") return parseInt(row.dataset.severityRank, 10) || 99;
      if (key === "state") return row.dataset.state || "";
      if (key === "assignee") return row.dataset.assignee || "";
      if (key === "due") return parseInt(row.dataset.dueSort, 10) || Number.MAX_SAFE_INTEGER;
      if (key === "id") return parseInt(row.dataset.id, 10) || 0;
      return 0;
    }

    function compareSortValues(a, b) {
      if (typeof a === "number" && typeof b === "number") return a - b;
      return String(a).localeCompare(String(b), undefined, { sensitivity: "base" });
    }

    function sortTableRows(tbody, primary, secondary) {
      const keys = [primary, secondary].filter(key => key && key !== "none");
      const rows = [...tbody.querySelectorAll("tr[data-categories]")];
      const emptyRows = [...tbody.querySelectorAll("tr.filter-empty")];
      rows.sort((left, right) => {
        for (const key of keys) {
          const cmp = compareSortValues(getSortValue(left, key), getSortValue(right, key));
          if (cmp !== 0) return cmp;
        }
        return compareSortValues(getSortValue(left, "id"), getSortValue(right, "id"));
      });
      rows.forEach(row => tbody.appendChild(row));
      emptyRows.forEach(row => tbody.appendChild(row));
    }

    function getSelectedAssignees(controls) {
      const allCheckbox = controls.querySelector(".assignee-all input");
      if (allCheckbox?.checked) return null;
      return [...controls.querySelectorAll('.assignee-menu input:checked:not([value="__all__"])')]
        .map(input => input.value);
    }

    function updateAssigneeButtonLabel(controls) {
      const button = controls.querySelector(".assignee-filter-btn");
      const selected = getSelectedAssignees(controls);
      if (!button) return;
      if (selected === null) {
        button.textContent = "Assignees: All";
        return;
      }
      if (selected.length === 0) {
        button.textContent = "Assignees: None selected";
        return;
      }
      if (selected.length <= 2) {
        button.textContent = `Assignees: ${selected.join(", ")}`;
        return;
      }
      button.textContent = `Assignees: ${selected.length} selected`;
    }

    function getActiveCategoryFilters(controls) {
      const allTab = controls.querySelector('.state-tab[data-filter="all"]');
      if (allTab?.classList.contains("active")) return null;
      const active = [...controls.querySelectorAll(".state-tab.active")]
        .map(tab => tab.dataset.filter)
        .filter(key => key !== "all");
      return active.length ? active : null;
    }

    function categoryFilterLabel(controls) {
      const active = getActiveCategoryFilters(controls);
      if (active === null) return "All categories";
      if (active.length === 1) {
        const tab = [...controls.querySelectorAll(".state-tab.active")]
          .find(t => t.dataset.filter === active[0]);
        return tab ? tab.textContent.replace(/\\s*\\(\\d+\\)$/, "") : active[0];
      }
      return `${active.length} categories`;
    }

    function applyTableFilters(controls) {
      const tbody = document.getElementById(controls.dataset.target);
      if (!tbody) return;

      const categoryFilters = getActiveCategoryFilters(controls);
      const assigneeFilters = getSelectedAssignees(controls);
      let visible = 0;

      tbody.querySelectorAll("tr[data-categories]").forEach(row => {
        const categories = row.dataset.categories ? row.dataset.categories.split("|") : [];
        const categoryMatch = categoryFilters === null
          || categoryFilters.some(key => categories.includes(key));
        const assigneeMatch = assigneeFilters === null
          || assigneeFilters.includes(row.dataset.assignee);
        const match = categoryMatch && assigneeMatch;
        row.style.display = match ? "" : "none";
        if (match) visible += 1;
      });

      const emptyRow = tbody.querySelector("tr.filter-empty");
      if (emptyRow) emptyRow.style.display = visible === 0 ? "" : "none";

      const primary = controls.querySelector(".sort-primary")?.value || "priority";
      const secondary = controls.querySelector(".sort-secondary")?.value || "severity";
      sortTableRows(tbody, primary, secondary);

      const countEl = controls.querySelector(".filter-count");
      if (countEl) {
        const assigneeLabel = assigneeFilters === null
          ? "all assignees"
          : `${assigneeFilters.length} assignee(s)`;
        const sortLabel = secondary === "none"
          ? primary
          : `${primary} → ${secondary}`;
        countEl.textContent =
          `Showing ${visible} item(s) · ${categoryFilterLabel(controls)} · ${assigneeLabel} · Sort: ${sortLabel}`;
      }
    }

    function resetTableControls(controls) {
      controls.querySelectorAll(".state-tab").forEach(tab => {
        tab.classList.toggle("active", tab.dataset.filter === "all");
      });
      controls.querySelectorAll('.assignee-menu input[type="checkbox"]').forEach(input => {
        input.checked = true;
      });
      const sortPrimary = controls.querySelector(".sort-primary");
      const sortSecondary = controls.querySelector(".sort-secondary");
      if (sortPrimary) sortPrimary.value = "priority";
      if (sortSecondary) sortSecondary.value = "severity";
      updateAssigneeButtonLabel(controls);
      applyTableFilters(controls);
    }

    function initTableControls(container) {
      container.querySelectorAll(".table-controls").forEach(controls => {
        const filterBar = controls.querySelector(".state-filter-bar");
        const assigneeMenu = controls.querySelector(".assignee-menu");
        const assigneeButton = controls.querySelector(".assignee-filter-btn");

        filterBar?.addEventListener("click", e => {
          const tab = e.target.closest(".state-tab");
          if (!tab || !filterBar.contains(tab)) return;
          const key = tab.dataset.filter;
          const allTab = controls.querySelector('.state-tab[data-filter="all"]');
          if (key === "all") {
            controls.querySelectorAll(".state-tab").forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
          } else {
            allTab?.classList.remove("active");
            tab.classList.toggle("active");
            const selected = controls.querySelectorAll('.state-tab.active:not([data-filter="all"])');
            if (selected.length === 0) allTab?.classList.add("active");
          }
          applyTableFilters(controls);
        });

        assigneeButton?.addEventListener("click", e => {
          e.stopPropagation();
          const open = assigneeMenu.classList.toggle("open");
          assigneeButton.setAttribute("aria-expanded", open ? "true" : "false");
        });

        assigneeMenu?.addEventListener("change", e => {
          const input = e.target;
          if (input.value === "__all__") {
            controls.querySelectorAll('.assignee-menu input[type="checkbox"]').forEach(box => {
              box.checked = input.checked;
            });
          } else {
            const allBox = controls.querySelector('.assignee-all input');
            const boxes = [...controls.querySelectorAll('.assignee-menu input:not([value="__all__"])')];
            allBox.checked = boxes.length > 0 && boxes.every(box => box.checked);
          }
          updateAssigneeButtonLabel(controls);
          applyTableFilters(controls);
        });

        controls.querySelector(".sort-primary")?.addEventListener("change", () => applyTableFilters(controls));
        controls.querySelector(".sort-secondary")?.addEventListener("change", () => applyTableFilters(controls));
        controls.querySelector(".clear-filters-btn")?.addEventListener("click", () => resetTableControls(controls));

        updateAssigneeButtonLabel(controls);
        applyTableFilters(controls);
      });
    }

    function renderReport(a, containerId) {
      if (!a) {
        document.getElementById(containerId).innerHTML = '<p class="empty">No data available. Check configuration.</p>';
        return;
      }
      const ex = a.executive;
      const det = a.detailed;
      const k = ex.kpis;
      const dk = det.kpis;
      const maxS = Math.max(...ex.state_chart.map(r => r.count), 1);
      const maxP = Math.max(...ex.priority_chart.map(r => r.count), 1);
      const severityChart = ex.severity_chart || [];
      const maxSev = Math.max(...severityChart.map(r => r.count), 1);

      const detailItems = det.tracker_items || [];
      const filterTabs = det.filter_tabs || [];
      const detailTbodyId = `${containerId}-detail-items`;
      const allTbodyId = `${containerId}-all-items`;
      const detailControlsId = `${containerId}-detail-controls`;
      const allControlsId = `${containerId}-all-controls`;

      const detailRows = detailItems.map(renderDetailRow).join("");
      const itemRows = a.items.map(renderAllItemRow).join("");

      const detailControls = buildTableControls(
        filterTabs, detailItems, detailTbodyId, detailControlsId
      );
      const allControls = buildTableControls(
        filterTabs, a.items, allTbodyId, allControlsId
      );

      const assigneeLine = det.by_assignee.length
        ? '<strong>Open by assignee:</strong> ' + det.by_assignee.map(r => `${esc(r.assignee)} (${r.open})`).join(", ")
        : "";

      const recs = a.recommendations.map(r => `
        <li>
          <span class="rec-priority ${r.priority}">${r.priority}</span>
          <strong>${esc(r.action)}</strong>
          <div class="rec-rationale">${esc(r.rationale)}</div>
          ${renderRecLinks(r.related_items || [])}
        </li>`).join("");

      const trendClass = a.trends.trend === "improving" ? "improving" : a.trends.trend === "worsening" ? "worsening" : "";

      document.getElementById(containerId).innerHTML = `
        <div class="expand-card open" data-card>
          <div class="expand-header" onclick="toggleCard(this)">
            <h2>Executive Summary</h2><span class="chevron">▼</span>
          </div>
          <div class="expand-body">
            <div class="exec-panel">
              <div class="exec-summary-box">${esc(ex.summary)}</div>
              <div class="headline">${esc(a.headline)}</div>
              <div class="progress-label">Completion — ${k.completion_pct}% (${k.closed} of ${k.total})</div>
              <div class="progress-track"><div class="progress-fill" style="width:${k.completion_pct}%"></div></div>
              <div class="kpi-grid">
                <div class="kpi"><div class="kpi-value warning">${k.open}</div><div class="kpi-label">Open</div></div>
                <div class="kpi"><div class="kpi-value success">${k.closed}</div><div class="kpi-label">Closed</div></div>
                <div class="kpi"><div class="kpi-value danger">${k.critical_open}</div><div class="kpi-label">Critical open</div></div>
                <div class="kpi"><div class="kpi-value">${k.high_priority_open}</div><div class="kpi-label">High+ priority open</div></div>
                <div class="kpi"><div class="kpi-value danger">${k.overdue}</div><div class="kpi-label">Overdue</div></div>
                <div class="kpi"><div class="kpi-value success">${k.closed_this_week}</div><div class="kpi-label">Closed this week</div></div>
              </div>
              <div class="panels">
                <div class="panel"><h3>Status distribution</h3>${renderBars(ex.state_chart)}</div>
                <div class="panel"><h3>Priority (open items)</h3>${renderBars(ex.priority_chart)}</div>
              </div>
              ${severityChart.length ? `<div class="panels" style="margin-top:14px">
                <div class="panel"><h3>Severity (open items)</h3>${renderBars(severityChart, maxSev)}</div>
              </div>` : ""}
            </div>
          </div>
        </div>

        <div class="expand-card" data-card>
          <div class="expand-header" onclick="toggleCard(this)">
            <h2>Detailed View</h2><span class="chevron">▼</span>
          </div>
          <div class="expand-body">
            <div class="detail-panel">
              <h3>${esc(det.title)}</h3>
              <div class="sub">${esc(det.subtitle)}</div>
              <div class="narrative">${esc(det.summary)}</div>
              <div class="kpi-grid">
                <div class="kpi"><div class="kpi-value">${dk.total_tracked}</div><div class="kpi-label">Total tracked</div></div>
                <div class="kpi"><div class="kpi-value warning">${dk.open}</div><div class="kpi-label">Open</div></div>
                <div class="kpi"><div class="kpi-value success">${dk.closed}</div><div class="kpi-label">Resolved (${dk.resolution_pct}%)</div></div>
                <div class="kpi"><div class="kpi-value danger">${dk.critical_open}</div><div class="kpi-label">Critical open (P1)</div></div>
                <div class="kpi"><div class="kpi-value">${dk.in_review}</div><div class="kpi-label">In PR review</div></div>
                <div class="kpi"><div class="kpi-value success">${dk.closed_this_week}</div><div class="kpi-label">Closed this week</div></div>
                <div class="kpi"><div class="kpi-value danger">${dk.overdue_open}</div><div class="kpi-label">Overdue open</div></div>
                <div class="kpi"><div class="kpi-value warning">${dk.stale_open}</div><div class="kpi-label">Stale (7+ days)</div></div>
              </div>
              <div><strong>Resolution progress</strong></div>
              <div class="progress-track"><div class="progress-fill" style="width:${dk.resolution_pct}%"></div></div>
              ${detailControls}
              ${assigneeLine ? `<div class="assignee-line">${assigneeLine}</div>` : ""}
              <table>
                <thead><tr>
                  <th>ID</th><th>Title</th><th>Work Item Type</th><th>Priority</th><th>Severity</th><th>State</th>
                  <th>Assignee</th><th>Due Date</th><th>Created</th><th>Age</th><th>Last update</th>
                </tr></thead>
                <tbody id="${detailTbodyId}">
                  ${detailRows || '<tr class="filter-empty"><td colspan="11" class="empty">No items.</td></tr>'}
                  ${detailRows ? '<tr class="filter-empty" style="display:none"><td colspan="11" class="empty">No items match this filter.</td></tr>' : ""}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div class="section-title">Query Results (${a.item_count} items)</div>
        <div class="expand-card open" data-card>
          <div class="expand-header" onclick="toggleCard(this)">
            <h2>All Items</h2><span class="chevron">▼</span>
          </div>
          <div class="expand-body">
            ${allControls}
            <table>
              <thead><tr>
                <th>ID</th><th>Title</th><th>Type</th><th>State</th>
                <th>Priority</th><th>Severity</th><th>Assignee</th><th>Due</th>
              </tr></thead>
              <tbody id="${allTbodyId}">
                ${itemRows || '<tr class="filter-empty"><td colspan="8" class="empty">No items.</td></tr>'}
                ${itemRows ? '<tr class="filter-empty" style="display:none"><td colspan="8" class="empty">No items match this filter.</td></tr>' : ""}
              </tbody>
            </table>
          </div>
        </div>

        <div class="section-title">Activity Trend (Last 7 Days)</div>
        <div class="expand-card open" data-card>
          <div class="expand-header" onclick="toggleCard(this)">
            <h2>7-Day Activity &amp; Trend</h2><span class="chevron">▼</span>
          </div>
          <div class="expand-body">
            <div class="trend-grid">
              <div class="trend-card worsening"><div class="val">${a.trends.items_created_7d}</div><div class="lbl">Items created</div></div>
              <div class="trend-card improving"><div class="val">${a.trends.items_closed_7d}</div><div class="lbl">Items closed</div></div>
              <div class="trend-card ${trendClass}"><div class="val">${a.trends.net_change >= 0 ? '+' : ''}${a.trends.net_change}</div><div class="lbl">Net change</div></div>
            </div>
            <div class="trend-summary">${esc(a.trends.trend_summary)} <span style="color:var(--muted)">(${esc(a.trends.period_label)})</span></div>
          </div>
        </div>

        <div class="section-title">Recommended Actions</div>
        <div class="expand-card open" data-card>
          <div class="expand-header" onclick="toggleCard(this)">
            <h2>PM Recommendations</h2><span class="chevron">▼</span>
          </div>
          <div class="expand-body">
            <ul class="rec-list">${recs}</ul>
          </div>
        </div>
      `;
      initTableControls(document.getElementById(containerId));
    }

    function toggleCard(header) {
      header.closest(".expand-card").classList.toggle("open");
    }

    function switchTab(tab) {
      activeTab = tab;
      document.querySelectorAll(".top-tab").forEach(t => t.classList.toggle("active", t.dataset.tab === tab));
      document.getElementById("sidebar").classList.toggle("visible", tab === "queries");
      document.getElementById("area-view").classList.toggle("hidden", tab !== "area");
      document.getElementById("query-view").classList.toggle("hidden", tab !== "queries");
      if (tab === "area") renderArea();
      else renderQuery(activeQueryId);
    }

    function renderArea() {
      if (!areaAnalysis) {
        document.getElementById("area-sub").textContent = "Set ADO_AREA_PATH in .env to enable this report.";
        document.getElementById("area-content").innerHTML = '<p class="empty">No area path configured.</p>';
        return;
      }
      document.getElementById("area-title").innerHTML =
        esc(areaAnalysis.name) + `<span class="health-badge ${areaAnalysis.health}">${areaAnalysis.health}</span>`;
      document.getElementById("area-sub").textContent = areaAnalysis.path + " · " + areaAnalysis.item_count + " items";
      renderReport(areaAnalysis, "area-content");
    }

    function renderQuery(id) {
      const a = queryAnalyses[id];
      if (!a) return;
      document.getElementById("query-title").innerHTML =
        esc(a.name) + `<span class="health-badge ${a.health}">${a.health}</span>`;
      document.getElementById("query-sub").textContent = a.path + " · " + a.item_count + " items";
      renderReport(a, "query-content");
    }

    function selectQuery(id) {
      activeQueryId = id;
      document.querySelectorAll(".query-btn").forEach(b => b.classList.toggle("active", b.dataset.id === id));
      renderQuery(id);
    }

    document.querySelectorAll(".top-tab").forEach(t => t.addEventListener("click", () => switchTab(t.dataset.tab)));
    document.getElementById("query-list").addEventListener("click", e => {
      const btn = e.target.closest(".query-btn");
      if (btn) selectQuery(btn.dataset.id);
    });
    document.getElementById("query-search").addEventListener("input", e => {
      const term = e.target.value.toLowerCase();
      document.querySelectorAll(".query-btn").forEach(btn => {
        btn.style.display = btn.dataset.name.toLowerCase().includes(term) ? "block" : "none";
      });
    });

    document.addEventListener("click", e => {
      document.querySelectorAll(".assignee-menu.open").forEach(menu => {
        if (!menu.closest(".assignee-filter")?.contains(e.target)) {
          menu.classList.remove("open");
          menu.closest(".assignee-filter")
            ?.querySelector(".assignee-filter-btn")
            ?.setAttribute("aria-expanded", "false");
        }
      });
    });

    switchTab("area");
  </script>
</body>
</html>
"""
