#!/usr/bin/env python3
"""policy-as-code-linter

Lints a lightweight, vendor-neutral policy-as-code YAML format.

Expected input shape (YAML):

- id: read-orders
  effect: allow|deny
  actions: ["orders.read", ...]
  resources: ["orders/*", ...]
  principals: ["role:analyst", "user:alice"]  # optional
  description: "..."  # optional

Outputs human-readable findings and optional JSON report.

Dependencies:
- pyyaml (allowed by repo rules)
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import yaml


KABAB_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass
class Finding:
    severity: str  # error|warning|info
    rule_id: str
    code: str
    message: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "severity": self.severity,
            "rule_id": self.rule_id,
            "code": self.code,
            "message": self.message,
        }


def _is_wildcard(value: str) -> bool:
    v = value.strip().lower()
    return v in {"*", "all", "everyone", "any"}


def lint_policy(doc: Any) -> Dict[str, Any]:
    findings: List[Finding] = []

    if not isinstance(doc, list):
        findings.append(Finding("error", "<file>", "top_level_not_list", "Top-level YAML must be a list of rules."))
        return _finalize(findings)

    seen_ids = set()

    for i, rule in enumerate(doc):
        rid = f"rule[{i}]"
        if isinstance(rule, dict) and isinstance(rule.get("id"), str):
            rid = rule["id"]

        if not isinstance(rule, dict):
            findings.append(Finding("error", rid, "rule_not_object", "Each rule must be a mapping/object."))
            continue

        # Required fields
        for field in ["id", "effect", "actions", "resources"]:
            if field not in rule:
                findings.append(Finding("error", rid, "missing_field", f"Missing required field '{field}'."))

        rule_id = rule.get("id")
        if isinstance(rule_id, str):
            if rule_id in seen_ids:
                findings.append(Finding("error", rule_id, "duplicate_id", "Duplicate rule id."))
            seen_ids.add(rule_id)
            if not KABAB_ID_RE.match(rule_id):
                findings.append(Finding("info", rule_id, "id_style", "Rule id should be kebab-case (lowercase with hyphens)."))
        else:
            findings.append(Finding("error", rid, "id_not_string", "Rule id must be a string."))

        effect = rule.get("effect")
        if effect not in {"allow", "deny"}:
            findings.append(Finding("error", rid, "invalid_effect", "Effect must be 'allow' or 'deny'."))

        actions = rule.get("actions")
        if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
            findings.append(Finding("error", rid, "invalid_actions", "Actions must be a list of strings."))
            actions_list: List[str] = []
        else:
            actions_list = actions

        resources = rule.get("resources")
        if not isinstance(resources, list) or not all(isinstance(r, str) for r in resources):
            findings.append(Finding("error", rid, "invalid_resources", "Resources must be a list of strings."))
            resources_list: List[str] = []
        else:
            resources_list = resources

        principals = rule.get("principals")
        principals_list: List[str] = []
        if principals is None:
            principals_list = []
        elif not isinstance(principals, list) or not all(isinstance(p, str) for p in principals):
            findings.append(Finding("error", rid, "invalid_principals", "Principals must be a list of strings if provided."))
        else:
            principals_list = principals

        # Safety checks
        if effect == "allow":
            if any(_is_wildcard(a) for a in actions_list):
                findings.append(Finding("warning", rid, "wildcard_action", "Allow rule contains wildcard action; consider narrowing."))
            if any(_is_wildcard(r) or r.strip().endswith(":*") for r in resources_list):
                findings.append(Finding("warning", rid, "wildcard_resource", "Allow rule contains wildcard resource; consider narrowing."))

        if principals_list and any(_is_wildcard(p) for p in principals_list):
            findings.append(Finding("warning", rid, "wildcard_principal", "Rule contains wildcard principal; ensure this is intended."))

        if "description" not in rule:
            findings.append(Finding("info", rid, "missing_description", "Add a 'description' to aid review."))

    return _finalize(findings)


def _finalize(findings: List[Finding]) -> Dict[str, Any]:
    out = {
        "errors": [f.to_dict() for f in findings if f.severity == "error"],
        "warnings": [f.to_dict() for f in findings if f.severity == "warning"],
        "info": [f.to_dict() for f in findings if f.severity == "info"],
    }
    out["summary"] = {
        "errors": len(out["errors"]),
        "warnings": len(out["warnings"]),
        "info": len(out["info"]),
    }
    return out


def _print_table(report: Dict[str, Any]) -> None:
    rows = report["errors"] + report["warnings"] + report["info"]
    if not rows:
        print("No findings.")
        return

    print("severity\trule_id\tcode\tmessage")
    for r in rows:
        msg = r["message"].replace("\t", " ")
        print(f"{r['severity']}\t{r['rule_id']}\t{r['code']}\t{msg}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Lint a vendor-neutral policy-as-code YAML file.")
    ap.add_argument("--input", required=True, help="Path to policy YAML")
    ap.add_argument("--json-out", default=None, help="Optional path to write JSON report")
    args = ap.parse_args(argv)

    with open(args.input, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    report = lint_policy(doc)
    _print_table(report)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)

    # Non-zero exit if errors
    return 2 if report["summary"]["errors"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
