#!/usr/bin/env python3
"""Vendor-neutral prompt injection risk linter.

Scans prompt templates and representative retrieved content for common
prompt-injection patterns and missing safety boundaries.

Stdlib-only.
"""

import argparse
import json
import re
from typing import Dict, List


PATTERNS = [
    ("ignore_instructions", "high", re.compile(r"\b(ignore|disregard) (all|any|previous|prior) (instructions|rules)\b", re.I)),
    ("system_prompt_request", "high", re.compile(r"\b(reveal|show|print|dump) (the )?(system|developer) prompt\b", re.I)),
    ("tool_exfiltration", "high", re.compile(r"\b(send|post|email|upload) (your|the) (api key|token|credentials|secrets)\b", re.I)),
    ("role_escalation", "medium", re.compile(r"\b(you are now|act as) (a|an) (admin|root|developer mode)\b", re.I)),
    ("data_exfiltration", "medium", re.compile(r"\b(exfiltrate|leak|steal)\b", re.I)),
    ("jailbreak_phrases", "medium", re.compile(r"\bdo anything now\b|\bdan\b", re.I)),
]

BOUNDARY_CHECKS = [
    (
        "retrieved_untrusted_statement",
        "medium",
        re.compile(r"\b(untrusted|may be malicious|do not follow instructions from retrieved content)\b", re.I),
        "Add an explicit statement that retrieved content is untrusted and must not override instructions.",
    ),
    (
        "tool_use_constraints",
        "medium",
        re.compile(r"\b(tool|function) (use|calling) (is|are) (restricted|limited|allowed)\b", re.I),
        "Add explicit constraints for tool/function use (what is allowed, and what is never allowed).",
    ),
]


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def find_matches(text: str, scope: str) -> List[Dict]:
    findings = []
    for pid, sev, rx in PATTERNS:
        for m in rx.finditer(text):
            snippet = text[max(0, m.start() - 40) : m.end() + 40].replace("\n", " ")
            findings.append({"scope": scope, "type": pid, "severity": sev, "evidence": snippet[:200]})
            if len(findings) > 200:
                return findings
    return findings


def boundary_findings(prompt_text: str) -> List[Dict]:
    findings = []
    for cid, sev, rx, rec in BOUNDARY_CHECKS:
        if not rx.search(prompt_text):
            findings.append({"scope": "prompt", "type": cid, "severity": sev, "recommendation": rec})
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--retrieved", default=None)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    prompt_text = read_text(args.prompt)
    findings = []
    findings.extend(find_matches(prompt_text, "prompt"))
    findings.extend(boundary_findings(prompt_text))

    if args.retrieved:
        retrieved_text = read_text(args.retrieved)
        findings.extend(find_matches(retrieved_text, "retrieved"))

    summary = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        summary[f["severity"]] = summary.get(f["severity"], 0) + 1

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            {"summary": summary, "inputs": {"prompt": args.prompt, "retrieved": args.retrieved}, "findings": findings},
            f,
            indent=2,
            sort_keys=True,
        )

    return 2 if summary.get("high", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
