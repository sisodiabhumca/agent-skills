#!/usr/bin/env python3
"""Vendor-neutral cloud cost tag coverage auditor.

Reads a resource export CSV and optional tag policy JSON, then emits a coverage report.
Stdlib-only.
"""

import argparse
import csv
import json
import sys


def fnum(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def load_policy(path):
    if not path:
        return {"required_tags": [], "allowed_values": {}}
    with open(path, "r", encoding="utf-8") as f:
        pol = json.load(f)
    pol.setdefault("required_tags", [])
    pol.setdefault("allowed_values", {})
    return pol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--policy", required=False)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    policy = load_policy(args.policy)
    required = list(policy.get("required_tags", []))
    allowed_values = dict(policy.get("allowed_values", {}))

    rows = []
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        raise SystemExit("input CSV has no rows")

    cols = set(rows[0].keys())
    for col in ("resource_id", "service", "cost_monthly"):
        if col not in cols:
            raise SystemExit("CSV must include columns: resource_id, service, cost_monthly")

    tag_cols = sorted([c for c in cols if c.startswith("tag_")])

    # If no policy required tags provided, treat all tag_ columns as required (common auditing mode)
    if not required:
        required = tag_cols

    missing_by_tag = {t: {"missing_count": 0, "missing_cost": 0.0, "invalid_count": 0, "invalid_cost": 0.0} for t in required}

    total_cost = 0.0
    ok_cost = 0.0
    ok_rows = 0

    resource_findings = []

    for r in rows:
        cost = fnum(r.get("cost_monthly"))
        total_cost += cost
        failures = []

        for t in required:
            val = (r.get(t) or "").strip()
            if not val:
                missing_by_tag[t]["missing_count"] += 1
                missing_by_tag[t]["missing_cost"] += cost
                failures.append({"tag": t, "issue": "missing"})
                continue
            allowed = allowed_values.get(t)
            if isinstance(allowed, list) and allowed and val not in allowed:
                missing_by_tag[t]["invalid_count"] += 1
                missing_by_tag[t]["invalid_cost"] += cost
                failures.append({"tag": t, "issue": "invalid", "value": val})

        if not failures:
            ok_rows += 1
            ok_cost += cost
        else:
            resource_findings.append(
                {
                    "resource_id": r.get("resource_id"),
                    "service": r.get("service"),
                    "cost_monthly": cost,
                    "tag_values": {t: r.get(t) for t in required},
                    "failures": failures,
                }
            )

    coverage_rate = ok_rows / len(rows)
    cost_coverage_rate = (ok_cost / total_cost) if total_cost > 0 else 0.0

    # Top tags by missing cost impact
    missing_ranked = sorted(
        [
            {
                "tag": t,
                "missing_cost": round(v["missing_cost"], 4),
                "missing_count": v["missing_count"],
                "invalid_cost": round(v["invalid_cost"], 4),
                "invalid_count": v["invalid_count"],
            }
            for t, v in missing_by_tag.items()
        ],
        key=lambda x: (x["missing_cost"] + x["invalid_cost"]),
        reverse=True,
    )

    top_resources = sorted(resource_findings, key=lambda x: x["cost_monthly"], reverse=True)[: args.top]

    remediation_plan = {
        "priority_order": [t["tag"] for t in missing_ranked if (t["missing_cost"] + t["invalid_cost"]) > 0],
        "focus_first": top_resources[: min(5, len(top_resources))],
        "suggestions": [
            "Enforce required tags at provisioning time (IaC policy or pipeline checks)",
            "Backfill tags on high-cost resources first",
            "Define allowed values for environment and cost center to prevent drift",
        ],
    }

    out = {
        "coverage": {
            "rows": len(rows),
            "required_tags": required,
            "tag_columns_detected": tag_cols,
            "coverage_rate": round(coverage_rate, 4),
            "cost_coverage_rate": round(cost_coverage_rate, 4),
            "total_cost_monthly": round(total_cost, 4),
        },
        "missing_by_tag": missing_ranked,
        "top_resources_to_fix": top_resources,
        "remediation_plan": remediation_plan,
    }

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
