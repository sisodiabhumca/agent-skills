#!/usr/bin/env python3

import argparse
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

ISO_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)


def _parse_ts(ts: str) -> Optional[datetime]:
    ts = ts.strip()
    if not ts:
        return None
    if not ISO_RE.match(ts):
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _fmt_ts(dt: datetime) -> str:
    # Always render ISO 8601 with offset
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="seconds")


def _require(d: Dict[str, Any], key: str, errors: List[str]) -> Any:
    if key not in d:
        errors.append(f"Missing required field: {key}")
        return None
    return d.get(key)


def _get_milestones(events: List[Dict[str, Any]]) -> Dict[str, Optional[datetime]]:
    # Heuristic: choose first/last event and keyword-based detection/mitigation/resolution.
    parsed: List[Tuple[datetime, Dict[str, Any]]] = []
    for e in events:
        ts = e.get("timestamp")
        if not isinstance(ts, str):
            continue
        dt = _parse_ts(ts)
        if dt is None:
            continue
        parsed.append((dt, e))
    parsed.sort(key=lambda x: x[0])
    if not parsed:
        return {"start": None, "detection": None, "mitigation": None, "resolution": None}

    start = parsed[0][0]
    resolution = parsed[-1][0]

    detection = None
    mitigation = None

    for dt, e in parsed:
        text = (e.get("event") or "").lower()
        if detection is None and any(k in text for k in ["detected", "alert", "paged", "reported"]):
            detection = dt
        if mitigation is None and any(k in text for k in ["mitigated", "rollback", "disabled", "scaled", "hotfix"]):
            mitigation = dt

    return {
        "start": start,
        "detection": detection,
        "mitigation": mitigation,
        "resolution": resolution,
    }


def _md_escape(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n").strip()


def _render_action_items(items: List[Dict[str, Any]]) -> str:
    lines = ["| Action | Owner | Due date | Status |", "|---|---|---|---|"]
    if not items:
        lines.append("| (add corrective/preventive actions) | (owner) | (due) | planned |")
        return "\n".join(lines)

    for it in items:
        action = _md_escape(str(it.get("action", ""))) or "(missing action)"
        owner = _md_escape(str(it.get("owner", ""))) or "(unassigned)"
        due = _md_escape(str(it.get("due_date", ""))) or "(unspecified)"
        status = _md_escape(str(it.get("status", ""))) or "planned"
        lines.append(f"| {action} | {owner} | {due} | {status} |")
    return "\n".join(lines)


def draft_postmortem(data: Dict[str, Any]) -> Tuple[str, List[str]]:
    errors: List[str] = []

    title = _require(data, "title", errors)
    severity = _require(data, "severity", errors)
    start_ts = data.get("start_time")
    end_ts = data.get("end_time")

    events = data.get("timeline", [])
    if not isinstance(events, list):
        errors.append("timeline must be a list")
        events = []

    impact = data.get("impact", {})
    if not isinstance(impact, dict):
        errors.append("impact must be an object")
        impact = {}

    start_dt = _parse_ts(start_ts) if isinstance(start_ts, str) else None
    end_dt = _parse_ts(end_ts) if isinstance(end_ts, str) else None

    milestones = _get_milestones(events)

    # Prefer explicit start/end if valid.
    incident_start = start_dt or milestones["start"]
    incident_end = end_dt or milestones["resolution"]

    duration_line = ""
    if incident_start and incident_end:
        delta = incident_end - incident_start
        mins = int(delta.total_seconds() // 60)
        duration_line = f"Duration: {mins} minutes"

    customer_impact = _md_escape(str(impact.get("customer", "(not provided)")))
    internal_impact = _md_escape(str(impact.get("internal", "(not provided)")))
    metrics = impact.get("metrics", {})
    metrics_md = ""
    if isinstance(metrics, dict) and metrics:
        metrics_md = "\n".join([f"- **{_md_escape(str(k))}**: {_md_escape(str(v))}" for k, v in metrics.items()])
    else:
        metrics_md = "- (no metrics provided)"

    contrib = data.get("contributing_factors", [])
    if contrib is None:
        contrib = []
    if not isinstance(contrib, list):
        errors.append("contributing_factors must be a list")
        contrib = []

    went_well = data.get("went_well", [])
    if not isinstance(went_well, list):
        errors.append("went_well must be a list")
        went_well = []

    went_poorly = data.get("went_poorly", [])
    if not isinstance(went_poorly, list):
        errors.append("went_poorly must be a list")
        went_poorly = []

    action_items = data.get("action_items", [])
    if not isinstance(action_items, list):
        errors.append("action_items must be a list")
        action_items = []

    # Timeline rendering
    parsed_events: List[Tuple[Optional[datetime], str]] = []
    for e in events:
        ts = e.get("timestamp")
        ev = e.get("event")
        dt = _parse_ts(ts) if isinstance(ts, str) else None
        parsed_events.append((dt, _md_escape(str(ev)) if ev is not None else "(missing event)"))

    parsed_events.sort(key=lambda x: (x[0] is None, x[0] or datetime.max.replace(tzinfo=timezone.utc)))

    timeline_lines = []
    for dt, ev in parsed_events:
        ts_render = _fmt_ts(dt) if dt else "(invalid timestamp)"
        timeline_lines.append(f"- {ts_render} — {ev}")
    if not timeline_lines:
        timeline_lines = ["- (no timeline events provided)"]

    # Blameless narrative (template driven)
    narrative = data.get("summary", "")
    if not isinstance(narrative, str) or not narrative.strip():
        narrative = (
            "This incident was caused by an interaction between system behavior and operating conditions. "
            "The focus of this document is to understand what happened, how we responded, and what we will change to reduce recurrence."
        )

    lines: List[str] = []
    lines.append(f"# Postmortem: {_md_escape(str(title)) if title is not None else '(missing title)'}")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Severity: {_md_escape(str(severity)) if severity is not None else '(missing severity)'}")
    if incident_start:
        lines.append(f"- Start: {_fmt_ts(incident_start)}")
    else:
        lines.append("- Start: (unknown)")
    if incident_end:
        lines.append(f"- End: {_fmt_ts(incident_end)}")
    else:
        lines.append("- End: (unknown)")
    if duration_line:
        lines.append(f"- {duration_line}")
    if milestones.get("detection"):
        lines.append(f"- Detection: {_fmt_ts(milestones['detection'])}")
    if milestones.get("mitigation"):
        lines.append(f"- Mitigation: {_fmt_ts(milestones['mitigation'])}")
    lines.append("")
    lines.append(_md_escape(narrative))
    lines.append("")

    if errors:
        lines.append("## Input validation notes")
        for e in errors:
            lines.append(f"- {e}")
        lines.append("")

    lines.append("## Customer impact")
    lines.append(customer_impact)
    lines.append("")

    lines.append("## Internal impact")
    lines.append(internal_impact)
    lines.append("")

    lines.append("## Metrics")
    lines.append(metrics_md)
    lines.append("")

    lines.append("## Timeline")
    lines.extend(timeline_lines)
    lines.append("")

    lines.append("## Root cause and contributing factors (blameless)")
    if contrib:
        lines.extend([f"- {_md_escape(str(c))}" for c in contrib])
    else:
        lines.append("- (not provided)")
    lines.append("")

    lines.append("## Detection and response")
    lines.append("- What alerted us? (add details)")
    lines.append("- How quickly did we triage and mitigate? (add details)")
    lines.append("- Communications: customer/internal updates (add details)")
    lines.append("")

    lines.append("## What went well")
    if went_well:
        lines.extend([f"- {_md_escape(str(w))}" for w in went_well])
    else:
        lines.append("- (not provided)")
    lines.append("")

    lines.append("## What didn’t go well")
    if went_poorly:
        lines.extend([f"- {_md_escape(str(w))}" for w in went_poorly])
    else:
        lines.append("- (not provided)")
    lines.append("")

    lines.append("## Action items")
    lines.append(_render_action_items(action_items))
    lines.append("")

    lines.append("## Follow-ups and references")
    lines.append("- Related tickets/PRs: (add links)")
    lines.append("- Dashboards/logs: (add links)")

    return "\n".join(lines).rstrip() + "\n", errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Draft a blameless incident postmortem from JSON inputs")
    ap.add_argument("--input", required=True, help="Path to incident JSON")
    ap.add_argument("--output", required=True, help="Path to write Markdown")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise SystemExit("Input JSON must be an object")

    md, _errors = draft_postmortem(data)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
