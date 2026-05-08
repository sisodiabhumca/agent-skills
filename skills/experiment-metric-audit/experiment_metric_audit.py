#!/usr/bin/env python3
"""experiment-metric-audit

Audits a vendor-neutral JSON metric definition file for common A/B testing pitfalls.

Expected input JSON:
{
  "experiment": {
    "name": "...",
    "description": "...",
    "variants": ["control", "treatment"],
    "analysis_window_days": 14
  },
  "metrics": [
    {
      "name": "conversion_rate",
      "type": "ratio",  # ratio|count|sum|average
      "unit": "user",    # user|session|order|event
      "window_days": 14,
      "numerator": "users_with_purchase",
      "denominator": "exposed_users",
      "direction": "increase"  # increase|decrease|neutral
    }
  ]
}

Outputs markdown + optional JSON report.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


ALLOWED_TYPES = {"ratio", "count", "sum", "average"}
ALLOWED_UNITS = {"user", "session", "order", "event"}
ALLOWED_DIRECTIONS = {"increase", "decrease", "neutral"}


@dataclass
class Finding:
    severity: str  # error|warning|info
    code: str
    metric: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "metric": self.metric,
            "message": self.message,
        }


def audit(doc: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Finding] = []

    exp = doc.get("experiment")
    if not isinstance(exp, dict):
        findings.append(Finding("error", "missing_experiment", "<file>", "Missing 'experiment' object."))
        return _finalize(findings)

    for field in ["name", "variants", "analysis_window_days"]:
        if field not in exp:
            findings.append(Finding("error", "missing_experiment_field", "<file>", f"Missing experiment field '{field}'."))

    variants = exp.get("variants")
    if not isinstance(variants, list) or len(variants) < 2:
        findings.append(Finding("error", "invalid_variants", "<file>", "Experiment 'variants' must be a list with 2+ entries."))

    metrics = doc.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        findings.append(Finding("error", "missing_metrics", "<file>", "Missing non-empty 'metrics' list."))
        return _finalize(findings)

    seen_names = set()

    desc = (exp.get("description") or "").lower()
    risky_change = any(k in desc for k in ["latency", "error", "pricing", "checkout", "payment", "auth"])

    has_guardrail = False

    for m in metrics:
        name = m.get("name") if isinstance(m, dict) else None
        metric_name = name if isinstance(name, str) else "<unknown>"

        if not isinstance(m, dict):
            findings.append(Finding("error", "metric_not_object", metric_name, "Each metric must be an object."))
            continue

        if not isinstance(name, str) or not name.strip():
            findings.append(Finding("error", "missing_metric_name", metric_name, "Metric missing non-empty 'name'."))
        else:
            if name in seen_names:
                findings.append(Finding("error", "duplicate_metric", name, "Duplicate metric name."))
            seen_names.add(name)

        mtype = m.get("type")
        if mtype not in ALLOWED_TYPES:
            findings.append(Finding("error", "invalid_type", metric_name, f"Metric type must be one of {sorted(ALLOWED_TYPES)}."))

        unit = m.get("unit")
        if unit not in ALLOWED_UNITS:
            findings.append(Finding("error", "invalid_unit", metric_name, f"Metric unit must be one of {sorted(ALLOWED_UNITS)}."))

        window = m.get("window_days")
        if not isinstance(window, int) or window <= 0:
            findings.append(Finding("warning", "missing_window", metric_name, "Set 'window_days' to a positive integer."))

        direction = m.get("direction")
        if direction not in ALLOWED_DIRECTIONS:
            findings.append(Finding("info", "missing_direction", metric_name, "Set 'direction' to increase/decrease/neutral."))

        if mtype == "ratio":
            num = m.get("numerator")
            den = m.get("denominator")
            if not isinstance(num, str) or not num.strip():
                findings.append(Finding("error", "missing_numerator", metric_name, "Ratio metric requires non-empty 'numerator'."))
            if not isinstance(den, str) or not den.strip():
                findings.append(Finding("error", "missing_denominator", metric_name, "Ratio metric requires non-empty 'denominator'."))

        # Heuristic: if metric is labeled guardrail
        role = (m.get("role") or "").lower()
        if role == "guardrail" or "error" in metric_name.lower() or "latency" in metric_name.lower():
            has_guardrail = True

        # Heuristic mismatch warning
        if isinstance(m.get("numerator_unit"), str) and isinstance(m.get("denominator_unit"), str):
            if m["numerator_unit"] != m["denominator_unit"] and mtype == "ratio":
                findings.append(
                    Finding(
                        "warning",
                        "unit_mismatch",
                        metric_name,
                        "Ratio metric numerator_unit and denominator_unit differ; ensure unit of analysis is consistent.",
                    )
                )

    if risky_change and not has_guardrail:
        findings.append(Finding("warning", "missing_guardrail", "<file>", "Experiment description suggests risk; add guardrail metrics (e.g., error rate/latency)."))

    return _finalize(findings)


def _finalize(findings: List[Finding]) -> Dict[str, Any]:
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    info = [f for f in findings if f.severity == "info"]

    # Simple score: start 100, subtract penalties
    score = 100
    score -= 25 * len(errors)
    score -= 10 * len(warnings)
    score -= 2 * len(info)
    if score < 0:
        score = 0

    return {
        "summary": {"errors": len(errors), "warnings": len(warnings), "info": len(info), "score": score},
        "errors": [f.to_dict() for f in errors],
        "warnings": [f.to_dict() for f in warnings],
        "info": [f.to_dict() for f in info],
    }


def format_markdown(report: Dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# Experiment metric audit\n",
        f"Score: **{s['score']}** (errors: {s['errors']}, warnings: {s['warnings']}, info: {s['info']})\n",
    ]

    def _section(title: str, rows: List[Dict[str, str]]) -> None:
        lines.append(f"## {title}\n")
        if not rows:
            lines.append("- None\n")
            return
        for r in rows:
            lines.append(f"- **{r['metric']}** ({r['code']}): {r['message']}")
        lines.append("")

    _section("Errors", report["errors"])
    _section("Warnings", report["warnings"])
    _section("Info", report["info"])

    return "\n".join(lines).strip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Audit an experiment metric-definition JSON for common pitfalls.")
    ap.add_argument("--input", required=True, help="Path to experiment JSON")
    ap.add_argument("--json-out", default=None, help="Optional path to write JSON report")
    args = ap.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as f:
        doc = json.load(f)

    report = audit(doc)
    print(format_markdown(report))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)

    return 2 if report["summary"]["errors"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
