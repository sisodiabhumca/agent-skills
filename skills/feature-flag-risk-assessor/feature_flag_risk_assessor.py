#!/usr/bin/env python3
"""Vendor-neutral feature flag risk assessor.

Heuristics to spot stale flags, missing ownership, conflicting targeting rules,
and missing kill-switch patterns.

Stdlib-only.
"""

import argparse
import datetime as dt
import json
from typing import Any, Dict, List, Tuple


def parse_date(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def days_ago(d: dt.date, today: dt.date) -> int:
    return (today - d).days


def get_rules_conflicts(rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Detect duplicate segment keys with different rollouts."""
    seen: Dict[str, List[Tuple[int, Any]]] = {}
    conflicts = []
    for i, r in enumerate(rules or []):
        seg = str(r.get("segment") or r.get("audience") or "")
        rollout = r.get("rollout")
        if not seg:
            continue
        seen.setdefault(seg, []).append((i, rollout))
    for seg, entries in seen.items():
        rollouts = {json.dumps(e[1], sort_keys=True, default=str) for e in entries}
        if len(entries) > 1 and len(rollouts) > 1:
            conflicts.append({"segment": seg, "rule_indexes": [e[0] for e in entries]})
    return conflicts


def has_kill_switch(flag: Dict[str, Any]) -> bool:
    """Best-effort check for an explicit override/kill-switch concept."""
    if flag.get("kill_switch") is True:
        return True
    for r in flag.get("rules") or []:
        seg = (r.get("segment") or r.get("audience") or "").lower()
        rollout = r.get("rollout")
        if seg in ("all", "everyone", "global") and (rollout == 0 or rollout == 0.0):
            return True
        if str(r.get("type") or "").lower() in ("override", "kill_switch", "kill-switch"):
            return True
    return False


def score_and_findings(
    flag: Dict[str, Any], stale_days: int, old_enabled_days: int, today: dt.date
) -> Tuple[int, List[Dict[str, Any]]]:
    findings = []
    score = 0

    key = flag.get("key")
    if not key:
        findings.append({"type": "schema", "severity": "high", "message": "Missing key"})
        return 100, findings

    created_at = flag.get("created_at")
    updated_at = flag.get("updated_at")
    enabled = bool(flag.get("enabled"))

    if not flag.get("owner"):
        findings.append({"type": "missing_owner", "severity": "medium", "message": "No owner specified"})
        score += 15

    if updated_at:
        d = days_ago(parse_date(updated_at), today)
        if d >= stale_days:
            findings.append({"type": "stale", "severity": "medium", "message": f"No updates in {d} days"})
            score += 20

    if enabled and created_at:
        d = days_ago(parse_date(created_at), today)
        if d >= old_enabled_days:
            findings.append({"type": "enabled_old", "severity": "medium", "message": f"Enabled flag created {d} days ago"})
            score += 15

    conflicts = get_rules_conflicts(flag.get("rules") or [])
    if conflicts:
        findings.append(
            {"type": "rule_conflict", "severity": "high", "message": "Conflicting rules for same segment", "details": conflicts}
        )
        score += 35

    if enabled and not has_kill_switch(flag):
        findings.append({"type": "missing_kill_switch", "severity": "high", "message": "Enabled flag has no apparent kill-switch/override"})
        score += 30

    score = min(100, score)
    return score, findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--stale-days", type=int, default=90)
    ap.add_argument("--old-enabled-days", type=int, default=180)
    ap.add_argument("--today", default=None, help="Override today's date (YYYY-MM-DD) for deterministic tests")
    args = ap.parse_args()

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    with open(args.input, "r", encoding="utf-8") as f:
        doc = json.load(f)

    flags = doc.get("flags") if isinstance(doc, dict) else None
    if not isinstance(flags, list):
        raise SystemExit("Input JSON must be an object with a 'flags' array")

    summary = {"missing_owner": 0, "stale": 0, "enabled_old": 0, "rule_conflict": 0, "missing_kill_switch": 0}
    out_flags = []

    for flag in flags:
        sc, finds = score_and_findings(flag, args.stale_days, args.old_enabled_days, today)
        for fnd in finds:
            t = fnd.get("type")
            if t in summary:
                summary[t] += 1
        out_flags.append({"key": flag.get("key"), "enabled": bool(flag.get("enabled")), "risk_score": sc, "findings": finds})

    report = {"summary": summary, "flags": out_flags, "assessed_at": str(today)}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    high = sum(1 for fl in out_flags for fnd in fl["findings"] if fnd.get("severity") == "high")
    return 2 if high else 0


if __name__ == "__main__":
    raise SystemExit(main())
