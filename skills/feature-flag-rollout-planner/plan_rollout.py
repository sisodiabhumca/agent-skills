#!/usr/bin/env python3

import argparse
import json
from typing import Any, Dict, List


def _as_list(x: Any) -> List[str]:
    if isinstance(x, list):
        return [str(i) for i in x if str(i).strip()]
    return []


def plan(feature: Dict[str, Any]) -> str:
    name = str(feature.get("name") or "(unnamed feature)")
    description = str(feature.get("description") or "(no description provided)")
    target = str(feature.get("target_users") or "(unspecified)")

    success = _as_list(feature.get("success_metrics"))
    guardrails = _as_list(feature.get("guardrail_metrics"))

    risks = feature.get("risks", {})
    if not isinstance(risks, dict):
        risks = {}

    risk_notes = _as_list(risks.get("notes"))
    data_migration = bool(risks.get("data_migration", False))
    perf_sensitive = bool(risks.get("performance_sensitive", False))
    external_deps = _as_list(risks.get("external_dependencies"))

    stakeholders = _as_list(feature.get("stakeholders"))

    phases = [
        {"phase": "Internal", "traffic": "employees/internal", "duration": "1-2 days"},
        {"phase": "Canary", "traffic": "1%", "duration": "1 day"},
        {"phase": "Ramp", "traffic": "10%", "duration": "2-3 days"},
        {"phase": "Scale", "traffic": "50%", "duration": "3-5 days"},
        {"phase": "Full", "traffic": "100%", "duration": "ongoing"},
    ]

    lines: List[str] = []
    lines.append(f"# Feature-flag rollout plan: {name}")
    lines.append("")
    lines.append("## Overview")
    lines.append(f"- Description: {description}")
    lines.append(f"- Target users: {target}")
    lines.append("")

    lines.append("## Risk profile")
    lines.append(f"- Data migration: {'yes' if data_migration else 'no'}")
    lines.append(f"- Performance sensitive: {'yes' if perf_sensitive else 'no'}")
    if external_deps:
        lines.append("- External dependencies:")
        lines.extend([f"  - {d}" for d in external_deps])
    else:
        lines.append("- External dependencies: (none listed)")
    if risk_notes:
        lines.append("- Notes:")
        lines.extend([f"  - {n}" for n in risk_notes])
    lines.append("")

    lines.append("## Metrics")
    lines.append("### Success metrics")
    if success:
        lines.extend([f"- {m}" for m in success])
    else:
        lines.append("- (add success metrics)")
    lines.append("")
    lines.append("### Guardrail metrics")
    if guardrails:
        lines.extend([f"- {m}" for m in guardrails])
    else:
        lines.append("- (add guardrail metrics)")
    lines.append("")

    lines.append("## Phased rollout")
    lines.append("| Phase | Traffic | Duration | Enablement criteria | Monitor | Rollback trigger |")
    lines.append("|---|---|---|---|---|---|")

    default_rb = "Error rate + latency regression vs baseline"
    for p in phases:
        enable = "All automated checks green; flag toggles verified"
        monitor = "Dashboards, logs, support signals"
        rb = default_rb
        if p["phase"] == "Internal":
            enable = "QA sign-off; internal stakeholders notified"
        if p["phase"] == "Full":
            monitor = "Weekly monitoring; keep flag for fast disable"

        lines.append(
            f"| {p['phase']} | {p['traffic']} | {p['duration']} | {enable} | {monitor} | {rb} |"
        )

    lines.append("")
    lines.append("## Monitoring and dashboards")
    lines.append("- Ensure dashboards exist for each success and guardrail metric.")
    lines.append("- Set alerts for error rate, latency, and saturation metrics.")
    if data_migration:
        lines.append("- Data migration: add backfill progress and consistency checks.")
    if perf_sensitive:
        lines.append("- Performance: monitor CPU, memory, and downstream service latency.")
    lines.append("")

    lines.append("## Rollback plan")
    lines.append("- Primary: disable the feature flag (instant mitigation).")
    lines.append("- Secondary: rollback the deploy if needed.")
    if data_migration:
        lines.append("- If migration is irreversible, define compensating steps and a forward-fix strategy.")
    lines.append("")

    lines.append("## Communications checklist")
    if stakeholders:
        lines.append("- Stakeholders:")
        lines.extend([f"  - {s}" for s in stakeholders])
    else:
        lines.append("- Stakeholders: (add list)")
    lines.append("- Announce internal rollout start and expected timeline.")
    lines.append("- Notify support/customer-facing teams before ramping beyond canary.")
    lines.append("- Post final update after full rollout.")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a staged rollout plan for a feature flag")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        feature = json.load(f)

    if not isinstance(feature, dict):
        raise SystemExit("Input must be a JSON object")

    md = plan(feature)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
