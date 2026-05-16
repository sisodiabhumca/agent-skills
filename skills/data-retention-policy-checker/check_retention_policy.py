#!/usr/bin/env python3

import argparse
import json
from typing import Any, Dict, List, Tuple


def _get_int(x: Any) -> Tuple[bool, int]:
    if isinstance(x, bool):
        return False, 0
    if isinstance(x, int):
        return True, x
    return False, 0


def _severity_rank(sev: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(sev, 0)


def check_policy(policy: Dict[str, Any]) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []

    legal_hold_supported = policy.get("legal_hold_supported")
    if legal_hold_supported is not True:
        findings.append(
            {
                "severity": "high",
                "dataset": "(policy)",
                "issue": "Legal hold support not confirmed.",
                "recommendation": "Document and implement a legal hold process that suspends deletion when required.",
            }
        )

    ok_backup, backup_days = _get_int(policy.get("backup_retention_days"))
    if not ok_backup or backup_days < 0:
        findings.append(
            {
                "severity": "medium",
                "dataset": "(policy)",
                "issue": "backup_retention_days missing or invalid.",
                "recommendation": "Set backup retention in days and ensure it is operationally achievable.",
            }
        )

    datasets = policy.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        findings.append(
            {
                "severity": "high",
                "dataset": "(policy)",
                "issue": "No datasets listed.",
                "recommendation": "List each dataset/system of record with classification and retention period.",
            }
        )
        return findings

    for ds in datasets:
        if not isinstance(ds, dict):
            continue
        name = str(ds.get("name") or "(unnamed)")
        data_class = str(ds.get("data_class") or "(unspecified)")
        system = str(ds.get("system") or "(unspecified)")

        ok_ret, retention_days = _get_int(ds.get("retention_days"))
        deletion_method = ds.get("deletion_method")

        if not name or name == "(unnamed)":
            findings.append(
                {
                    "severity": "medium",
                    "dataset": "(dataset)",
                    "issue": f"Dataset missing name (system={system}).",
                    "recommendation": "Provide a stable dataset name used in documentation and tooling.",
                }
            )

        if not ok_ret:
            findings.append(
                {
                    "severity": "high",
                    "dataset": name,
                    "issue": "retention_days missing or not an integer.",
                    "recommendation": "Set a retention period in days; avoid indefinite retention unless justified.",
                }
            )
            continue

        if retention_days == 0:
            findings.append(
                {
                    "severity": "low",
                    "dataset": name,
                    "issue": "Retention is 0 days (immediate deletion).",
                    "recommendation": "Confirm operational feasibility and whether any legal/finance requirements need longer retention.",
                }
            )

        if retention_days > 3650 and "personal" in data_class.lower():
            findings.append(
                {
                    "severity": "high",
                    "dataset": name,
                    "issue": f"Very long retention ({retention_days} days) for personal data.",
                    "recommendation": "Add justification and consider shorter retention or aggregation/anonymization.",
                }
            )

        if retention_days < 0:
            findings.append(
                {
                    "severity": "high",
                    "dataset": name,
                    "issue": "Negative retention_days value.",
                    "recommendation": "Use a non-negative integer number of days.",
                }
            )

        if not isinstance(deletion_method, str) or not deletion_method.strip():
            findings.append(
                {
                    "severity": "medium",
                    "dataset": name,
                    "issue": "Deletion method not specified.",
                    "recommendation": "Document whether deletion is hard delete, soft delete + purge, or TTL-based.",
                }
            )

        # Backup vs primary check
        if ok_backup and ok_ret and backup_days >= 0 and retention_days >= 0:
            if backup_days > retention_days * 2 and retention_days > 0:
                findings.append(
                    {
                        "severity": "medium",
                        "dataset": name,
                        "issue": f"Backup retention ({backup_days}d) is much longer than primary retention ({retention_days}d).",
                        "recommendation": "Confirm whether backups are excluded from retention targets or implement backup deletion/purge procedures.",
                    }
                )

        # System field sanity
        if system == "(unspecified)":
            findings.append(
                {
                    "severity": "low",
                    "dataset": name,
                    "issue": "System of record not specified.",
                    "recommendation": "Specify the system/location to ensure retention is enforceable.",
                }
            )

    return findings


def render_markdown(findings: List[Dict[str, str]]) -> str:
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "")
        if sev in counts:
            counts[sev] += 1

    lines: List[str] = []
    lines.append("# Data retention policy check")
    lines.append("")
    lines.append("This report is a preliminary, vendor-neutral checklist and is not legal advice.")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- High: {counts['high']}")
    lines.append(f"- Medium: {counts['medium']}")
    lines.append(f"- Low: {counts['low']}")
    lines.append("")
    lines.append("## Findings")
    lines.append("| Severity | Dataset | Issue | Recommendation |")
    lines.append("|---|---|---|---|")

    if not findings:
        lines.append("| (none) | (n/a) | No issues detected | (n/a) |")
    else:
        for f in sorted(findings, key=lambda x: -_severity_rank(x.get("severity", ""))):
            lines.append(
                "| {severity} | {dataset} | {issue} | {recommendation} |".format(
                    severity=f.get("severity", ""),
                    dataset=str(f.get("dataset", "")),
                    issue=str(f.get("issue", "")),
                    recommendation=str(f.get("recommendation", "")),
                )
            )

    lines.append("")
    lines.append("## Notes and assumptions")
    lines.append("- Validate findings with security/privacy and legal stakeholders.")
    lines.append("- Confirm that backup/log retention matches your deletion capabilities.")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Check a data retention policy JSON for common gaps")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        policy = json.load(f)

    if not isinstance(policy, dict):
        raise SystemExit("Input must be a JSON object")

    findings = check_policy(policy)
    md = render_markdown(findings)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
