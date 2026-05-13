#!/usr/bin/env python3
"""Vendor-neutral SBOM license risk checker.

Reads a CycloneDX JSON SBOM and evaluates component licenses against a policy.
Stdlib-only.
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_licenses(component: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    lic = component.get("licenses")
    if not lic:
        return out
    # CycloneDX: licenses: [{license:{id|name}}, {expression:"..."}]
    if isinstance(lic, list):
        for entry in lic:
            if not isinstance(entry, dict):
                continue
            if "expression" in entry and isinstance(entry["expression"], str):
                out.append(entry["expression"].strip())
            lobj = entry.get("license")
            if isinstance(lobj, dict):
                if isinstance(lobj.get("id"), str):
                    out.append(lobj["id"].strip())
                elif isinstance(lobj.get("name"), str):
                    out.append(lobj["name"].strip())
    return [x for x in out if x]


def classify(licenses: List[str], policy: Dict[str, Any]) -> str:
    allow = set(policy.get("allow") or [])
    deny = set(policy.get("deny") or [])
    warn = set(policy.get("warn") or [])

    if not licenses:
        return "unknown"

    # Most restrictive wins.
    for l in licenses:
        if l in deny:
            return "denied"
    for l in licenses:
        if l in warn:
            return "warn"
    for l in licenses:
        if l in allow:
            return "allowed"

    return "unknown"


def rationale(cls: str) -> str:
    return {
        "denied": "License is denied by policy",
        "warn": "License requires review by policy",
        "allowed": "License is allowed by policy",
        "unknown": "License is missing or not listed in policy",
    }[cls]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sbom", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    sbom = load_json(args.sbom)
    policy = load_json(args.policy)

    comps = sbom.get("components") or []
    if not isinstance(comps, list):
        comps = []

    findings = []
    for c in comps:
        if not isinstance(c, dict):
            continue
        lics = extract_licenses(c)
        cls = classify(lics, policy)
        findings.append(
            {
                "name": c.get("name"),
                "version": c.get("version"),
                "purl": c.get("purl"),
                "licenses": lics,
                "classification": cls,
                "rationale": rationale(cls),
            }
        )

    report = {
        "summary": {
            "components": len(findings),
            "denied": sum(1 for f in findings if f["classification"] == "denied"),
            "warn": sum(1 for f in findings if f["classification"] == "warn"),
            "allowed": sum(1 for f in findings if f["classification"] == "allowed"),
            "unknown": sum(1 for f in findings if f["classification"] == "unknown"),
        },
        "findings": findings,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
