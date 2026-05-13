#!/usr/bin/env python3
"""Vendor-neutral feature flag cleanup planner.

Consumes a JSON array of feature flags with metadata and emits a ranked plan.
Stdlib-only.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        # Accept YYYY-MM-DD or full ISO
        if len(s) == 10:
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def days_between(a: Optional[datetime], b: datetime) -> Optional[int]:
    if not a:
        return None
    return int((b - a).total_seconds() // 86400)


def prod_state(flag: Dict[str, Any]) -> Dict[str, Any]:
    envs = flag.get("environments") or {}
    return envs.get("prod") or {}


def is_active_rollout(prod: Dict[str, Any]) -> bool:
    pct = prod.get("percentage")
    if pct is None:
        return False
    try:
        pct = float(pct)
    except Exception:
        return False
    return 0 < pct < 100


def score_flag(flag: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    created = parse_dt(flag.get("created_at"))
    last_eval = parse_dt(flag.get("last_evaluated_at"))
    age_days = days_between(created, now)
    since_eval = days_between(last_eval, now)

    prod = prod_state(flag)
    state = (prod.get("state") or flag.get("default") or "").lower()
    pct = prod.get("percentage")

    active_rollout = is_active_rollout(prod)
    permanently_on = (state == "on") and (pct in (None, 100, "100", 100.0))
    permanently_off = (state == "off") and (pct in (None, 0, "0", 0.0))

    score = 0
    rationale = []

    if age_days is not None:
        score += min(age_days // 30, 12)  # cap at 12
        if age_days > 180:
            rationale.append(f"Old flag ({age_days}d)")

    if since_eval is None:
        score += 4
        rationale.append("Never evaluated (or missing telemetry)")
    else:
        score += min(since_eval // 30, 8)
        if since_eval > 120:
            rationale.append(f"Not evaluated recently ({since_eval}d)")

    if permanently_on:
        score += 5
        rationale.append("Permanently ON in prod")
    if permanently_off:
        score += 3
        rationale.append("Permanently OFF in prod")

    if active_rollout:
        score = max(score - 10, 0)
        rationale.append("Active rollout in prod (do not remove)")

    # Recommendation
    action = "keep"
    checklist: List[str] = []

    if active_rollout:
        action = "keep"
        checklist = [
            "Confirm rollout owner and success metrics",
            "Set a decision date to either complete rollout or roll back",
        ]
    else:
        if (permanently_on or permanently_off) and (since_eval is None or since_eval > 90):
            if permanently_on and (age_days is not None and age_days > 365):
                action = "migrate_to_config"
                checklist = [
                    "Confirm flag is used as a kill-switch/config",
                    "Create a static config or code constant replacement",
                    "Remove flag reads, then delete flag definition",
                ]
            else:
                action = "remove"
                checklist = [
                    "Search codebase for flag reads/writes",
                    "Remove dead branches guarded by the flag",
                    "Delete the flag from the flag service",
                    "Verify in prod with a canary deploy",
                ]
        else:
            action = "keep"
            checklist = ["Add/verify owner", "Add telemetry for evaluations", "Review again in 30 days"]

    return {
        "key": flag.get("key"),
        "owner": flag.get("owner"),
        "age_days": age_days,
        "days_since_last_evaluated": since_eval,
        "prod": prod,
        "score": int(score),
        "recommended_action": action,
        "rationale": rationale,
        "checklist": checklist,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flags", required=True, help="JSON array of feature flags")
    ap.add_argument("--out", help="Write plan JSON to this path")
    args = ap.parse_args()

    with open(args.flags, "r", encoding="utf-8") as f:
        flags = json.load(f)

    if not isinstance(flags, list):
        raise SystemExit("--flags must be a JSON array")

    now = datetime.now(timezone.utc)
    plan = [score_flag(fl, now) for fl in flags]
    plan_sorted = sorted(plan, key=lambda x: x.get("score", 0), reverse=True)

    report = {
        "summary": {
            "flags": len(plan_sorted),
            "remove": sum(1 for p in plan_sorted if p["recommended_action"] == "remove"),
            "migrate_to_config": sum(1 for p in plan_sorted if p["recommended_action"] == "migrate_to_config"),
            "keep": sum(1 for p in plan_sorted if p["recommended_action"] == "keep"),
        },
        "plan": plan_sorted,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
