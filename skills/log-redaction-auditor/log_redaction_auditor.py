#!/usr/bin/env python3
"""Vendor-neutral log redaction audit.

Scans logs for patterns that commonly indicate secrets/PII.
Writes a JSON report intended for CI checks and secure sharing workflows.

Stdlib-only.
"""

import argparse
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


DEFAULT_CONFIG = {
    "allowlist_substrings": [
        "example.com",
        "TEST_",
        "dummy",
        "redacted",
        "REDACTED",
        "0000000000",
    ],
    "rules": [
        {"id": "private_key_block", "severity": "high", "regex": r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"},
        {"id": "aws_access_key_id", "severity": "high", "regex": r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"},
        {"id": "generic_api_key", "severity": "high", "regex": r"\b(api[_-]?key|secret|token)\b\s*[:=]\s*([A-Za-z0-9_\-]{16,})"},
        {"id": "auth_header_bearer", "severity": "high", "regex": r"\bAuthorization\s*:\s*Bearer\s+([A-Za-z0-9_\-\.]{16,})"},
        {"id": "email", "severity": "medium", "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"},
        {"id": "phone", "severity": "medium", "regex": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"},
        {"id": "password_assignment", "severity": "high", "regex": r"\bpassword\b\s*[:=]\s*([^\s,;]{6,})"},
        {"id": "suspicious_markers", "severity": "low", "regex": r"\b(token=|access_token=|sessionid=|set-cookie:|x-api-key)\b"},
    ],
}

SEVERITY_ORDER = {"high": 3, "medium": 2, "low": 1}


@dataclass
class Finding:
    severity: str
    rule_id: str
    line_number: int
    match: str
    context: str


def load_config(path: Optional[str]) -> Dict:
    if not path:
        return DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as f:
        user_cfg = json.load(f)
    cfg = dict(DEFAULT_CONFIG)
    cfg.update(user_cfg)
    return cfg


def is_allowlisted(text: str, allowlist_substrings: List[str]) -> bool:
    return any(s and s in text for s in allowlist_substrings)


def scan_lines(lines: List[str], cfg: Dict, max_findings: int) -> List[Finding]:
    findings: List[Finding] = []
    compiled: List[Tuple[str, str, re.Pattern]] = [
        (r["id"], r["severity"], re.compile(r["regex"], re.IGNORECASE)) for r in cfg.get("rules", [])
    ]
    allowlist_substrings = cfg.get("allowlist_substrings", [])

    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        for rule_id, severity, rx in compiled:
            m = rx.search(line)
            if not m:
                continue
            snippet = m.group(0)
            if is_allowlisted(line, allowlist_substrings) or is_allowlisted(snippet, allowlist_substrings):
                continue
            findings.append(
                Finding(
                    severity=severity,
                    rule_id=rule_id,
                    line_number=idx,
                    match=snippet[:200],
                    context=line.strip()[:500],
                )
            )
            if len(findings) >= max_findings:
                return findings
    return findings


def build_report(findings: List[Finding]) -> Dict:
    summary = {"high": 0, "medium": 0, "low": 0, "by_rule": {}}
    for f in findings:
        summary[f.severity] = summary.get(f.severity, 0) + 1
        summary["by_rule"][f.rule_id] = summary["by_rule"].get(f.rule_id, 0) + 1

    examples: Dict[str, List[Dict]] = {}
    for f in sorted(findings, key=lambda x: (-SEVERITY_ORDER.get(x.severity, 0), x.line_number)):
        if len(examples.get(f.rule_id, [])) >= 3:
            continue
        examples.setdefault(f.rule_id, []).append(
            {"severity": f.severity, "line_number": f.line_number, "match": f.match, "context": f.context}
        )

    return {"summary": summary, "examples": examples, "findings": [f.__dict__ for f in findings]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--config", default=None)
    ap.add_argument("--max-findings", type=int, default=200)
    args = ap.parse_args()

    cfg = load_config(args.config)
    with open(args.input, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    findings = scan_lines(lines, cfg, args.max_findings)
    report = build_report(findings)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)

    return 2 if report["summary"].get("high", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
