#!/usr/bin/env python3
"""Vendor-neutral incident postmortem QA checklist generator (stdlib-only)."""

import argparse
import datetime as dt
import json
from typing import Any, Dict, List, Optional, Tuple


PHASE_KEYWORDS = {
    "detection": ["alert", "page", "detected", "monitor", "alarm"],
    "triage": ["triage", "investig", "hypothesis", "diagnos"],
    "mitigation": ["rollback", "mitigat", "disable", "feature flag", "throttle", "failover"],
    "recovery": ["recover", "restored", "resolved", "green", "stable"],
    "follow_up": ["postmortem", "action item", "follow-up", "retro"],
}


def parse_ts(s: str) -> dt.datetime:
    # Accept RFC3339-ish timestamps with optional Z
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return dt.datetime.fromisoformat(s)


def classify(desc: str) -> str:
    d = desc.lower()
    for phase, kws in PHASE_KEYWORDS.items():
        if any(k in d for k in kws):
            return phase
    return "other"


def analyze_timeline(events: List[Dict[str, Any]], gap_minutes: int = 30) -> Dict[str, Any]:
    parsed = []
    for e in events:
        if "ts" not in e or "desc" not in e:
            raise ValueError("Each event must contain ts and desc")
        t = parse_ts(str(e["ts"]))
        parsed.append((t, str(e["desc"])))

    parsed.sort(key=lambda x: x[0])

    gaps = []
    for i in range(1, len(parsed)):
        delta = parsed[i][0] - parsed[i - 1][0]
        if delta.total_seconds() / 60.0 >= gap_minutes:
            gaps.append({
                "from": parsed[i - 1][0].isoformat(),
                "to": parsed[i][0].isoformat(),
                "minutes": round(delta.total_seconds() / 60.0, 1),
            })

    phases = {}
    for t, desc in parsed:
        p = classify(desc)
        phases[p] = phases.get(p, 0) + 1

    return {
        "event_count": len(parsed),
        "is_sorted": True,
        "gaps": gaps,
        "phase_counts": phases,
        "start": parsed[0][0].isoformat() if parsed else None,
        "end": parsed[-1][0].isoformat() if parsed else None,
    }


def make_checks(meta: Dict[str, Any], analysis: Dict[str, Any], events: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    missing: List[str] = []

    def ok(cond: bool, rationale_ok: str, rationale_bad: str):
        return {
            "status": "pass" if cond else "needs_attention",
            "rationale": rationale_ok if cond else rationale_bad,
        }

    text = " ".join(str(e.get("desc", "")) for e in events).lower()

    checks: List[Dict[str, Any]] = []

    has_impact = bool(meta.get("impact")) or any(w in text for w in ["users", "customers", "%", "degraded", "outage"])
    c = ok(has_impact, "Impact appears to be described.", "No clear impact statement or quantification found.")
    if c["status"] != "pass":
        missing.append("Add customer impact: who/what was affected and how much.")
    checks.append({"id": "impact_statement", **c})

    has_detection = analysis.get("phase_counts", {}).get("detection", 0) > 0
    c = ok(has_detection, "Timeline includes detection/alerting events.", "No detection/alerting events found in timeline.")
    if c["status"] != "pass":
        missing.append("Add detection: what signaled the issue (alerts, monitors, reports).")
    checks.append({"id": "detection_signals", **c})

    has_mitigation = analysis.get("phase_counts", {}).get("mitigation", 0) > 0
    c = ok(has_mitigation, "Timeline includes mitigation actions.", "No mitigation actions found; include rollback/disable/failover steps.")
    if c["status"] != "pass":
        missing.append("Add mitigation actions: what was changed to stop/limit impact.")
    checks.append({"id": "mitigation_actions", **c})

    has_recovery = analysis.get("phase_counts", {}).get("recovery", 0) > 0 or bool(meta.get("end_ts"))
    c = ok(has_recovery, "Recovery/resolution is present.", "No recovery/resolution evidence; include when service returned to normal.")
    if c["status"] != "pass":
        missing.append("Add recovery: when and how the incident was resolved.")
    checks.append({"id": "recovery_resolution", **c})

    has_root_cause = bool(meta.get("root_cause")) or any(w in text for w in ["root cause", "caused by", "due to", "trigger"])
    c = ok(has_root_cause, "Root cause evidence appears to be present.", "No clear root cause evidence; add supporting logs/metrics/changes.")
    if c["status"] != "pass":
        missing.append("Add root cause with evidence (logs, metrics, deploy diff, config change).")
    checks.append({"id": "root_cause_evidence", **c})

    action_items = meta.get("action_items") or []
    has_ai = isinstance(action_items, list) and len(action_items) > 0
    c = ok(has_ai, "Action items are listed.", "No action items provided.")
    if c["status"] != "pass":
        missing.append("Add follow-ups: specific action items to prevent recurrence.")
    checks.append({"id": "action_items_present", **c})

    # quality check for owners/due dates
    missing_owner = 0
    missing_due = 0
    if isinstance(action_items, list):
        for ai in action_items:
            if not isinstance(ai, dict):
                continue
            if not ai.get("owner"):
                missing_owner += 1
            if not ai.get("due"):
                missing_due += 1

    c = ok(missing_owner == 0 and missing_due == 0, "Action items include owners and due dates.", f"{missing_owner} action items missing owner; {missing_due} missing due date.")
    if c["status"] != "pass":
        missing.append("Ensure every action item has an owner and due date.")
    checks.append({"id": "action_items_accountability", **c})

    # timeline gaps
    gaps = analysis.get("gaps") or []
    c = ok(len(gaps) == 0, "No large gaps detected in timeline.", f"Timeline has {len(gaps)} gaps >= 30 minutes; add missing events.")
    if c["status"] != "pass":
        missing.append("Fill timeline gaps with key decisions and observations.")
    checks.append({"id": "timeline_continuity", **c})

    return checks, missing


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeline", required=True, help="Timeline JSON path")
    ap.add_argument("--out", required=True, help="Output report path")
    args = ap.parse_args()

    with open(args.timeline, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict) and "events" in payload:
        meta = {k: v for k, v in payload.items() if k != "events"}
        events = payload["events"]
    else:
        meta = {}
        events = payload

    if not isinstance(events, list):
        raise ValueError("Timeline must be a list of events or an object with events")

    analysis = analyze_timeline(events)
    checks, missing = make_checks(meta, analysis, events)

    report = {
        "timeline_analysis": analysis,
        "checks": checks,
        "missing_evidence": missing,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote checklist to {args.out}")


if __name__ == "__main__":
    main()
