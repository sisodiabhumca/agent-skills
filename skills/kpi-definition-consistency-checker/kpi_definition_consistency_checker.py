#!/usr/bin/env python3
"""Vendor-neutral KPI definition consistency checker (stdlib-only)."""

import argparse
import json
import re
from typing import Any, Dict, List, Tuple


def norm_name(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fingerprint(kpi: Dict[str, Any]) -> str:
    # Coarse fingerprint for definition conflicts
    parts = [
        str(kpi.get("numerator", "")).strip().lower(),
        str(kpi.get("denominator", "")).strip().lower(),
        str(kpi.get("grain", "")).strip().lower(),
        str(kpi.get("window", "")).strip().lower(),
    ]
    return "|".join(parts)


def validate(kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    by_norm: Dict[str, List[Dict[str, Any]]] = {}
    for k in kpis:
        n = norm_name(str(k.get("name", "")))
        by_norm.setdefault(n, []).append(k)

    duplicate_groups = []
    for n, group in by_norm.items():
        if n and len(group) > 1:
            duplicate_groups.append({
                "normalized_name": n,
                "names": [g.get("name") for g in group],
                "count": len(group),
            })

    # required fields
    required = ["name", "description", "numerator", "denominator", "grain", "window", "owner"]
    for k in kpis:
        for r in required:
            if not str(k.get(r, "")).strip():
                issues.append({
                    "severity": "high" if r in {"name", "numerator", "denominator"} else "medium",
                    "kpi": k.get("name", ""),
                    "problem": "missing_field",
                    "details": {"field": r},
                })

    # conflicts for same normalized name
    for n, group in by_norm.items():
        if not n or len(group) < 2:
            continue
        fps = {}
        for g in group:
            fp = fingerprint(g)
            fps.setdefault(fp, []).append(g.get("name"))
        if len(fps) > 1:
            issues.append({
                "severity": "high",
                "kpi": n,
                "problem": "definition_conflict",
                "details": {"variants": [{"fingerprint": fp, "names": names} for fp, names in fps.items()]},
            })

        # grain mismatches even if other fields same
        grains = sorted({str(g.get("grain", "")).strip().lower() for g in group if str(g.get("grain", "")).strip()})
        if len(grains) > 1:
            issues.append({
                "severity": "high",
                "kpi": n,
                "problem": "grain_mismatch",
                "details": {"grains": grains, "names": [g.get("name") for g in group]},
            })

        windows = sorted({str(g.get("window", "")).strip().lower() for g in group if str(g.get("window", "")).strip()})
        if len(windows) > 1:
            issues.append({
                "severity": "medium",
                "kpi": n,
                "problem": "window_mismatch",
                "details": {"windows": windows, "names": [g.get("name") for g in group]},
            })

    summary = {
        "kpi_count": len(kpis),
        "issue_count": len(issues),
        "duplicate_group_count": len(duplicate_groups),
    }

    # sort issues by severity
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda x: (sev_rank.get(x["severity"], 9), norm_name(str(x.get("kpi", ""))), x.get("problem", "")))

    return {"summary": summary, "issues": issues, "duplicate_groups": duplicate_groups}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kpis", required=True, help="Input KPI dictionary JSON")
    ap.add_argument("--out", required=True, help="Output report JSON")
    args = ap.parse_args()

    with open(args.kpis, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict) and "kpis" in payload:
        kpis = payload["kpis"]
    else:
        kpis = payload

    if not isinstance(kpis, list):
        raise ValueError("kpis input must be a list or object with kpis")

    for k in kpis:
        if not isinstance(k, dict):
            raise ValueError("each KPI must be an object")

    report = validate(kpis)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote KPI consistency report to {args.out}")


if __name__ == "__main__":
    main()
