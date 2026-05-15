#!/usr/bin/env python3
"""Vendor-neutral accessibility alt-text auditor (stdlib-only)."""

import argparse
import json
import os
import re
from typing import Any, Dict, List, Tuple


GENERIC_PATTERNS = [
    r"^image$", r"^photo$", r"^picture$", r"^img$", r"^screenshot$",
    r"^logo$", r"^banner$", r"^icon$",
]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def looks_like_filename(text: str) -> bool:
    t = text.strip().lower()
    return bool(re.search(r"\.(png|jpg|jpeg|gif|webp|svg)$", t)) or ("_" in t and len(t) < 40)


def is_generic(text: str) -> bool:
    t = text.strip().lower()
    if any(re.match(p, t) for p in GENERIC_PATTERNS):
        return True
    if looks_like_filename(t):
        return True
    return False


def audit(records: List[Dict[str, Any]], policy: Dict[str, Any]) -> Dict[str, Any]:
    min_len = int(policy.get("min_len", 5))
    max_len = int(policy.get("max_len", 140))
    allow_decorative_empty = bool(policy.get("allow_decorative_empty", True))

    issues: List[Dict[str, Any]] = []

    total = 0
    missing = 0
    empty = 0
    ok = 0

    for r in records:
        total += 1
        page = r.get("page", "")
        src = r.get("src", "")
        alt = r.get("alt")
        decorative = bool(r.get("decorative", False))

        finding = {
            "page": page,
            "src": src,
            "alt": alt,
            "decorative": decorative,
            "severity": "ok",
            "problems": [],
            "hint": None,
        }

        if alt is None:
            missing += 1
            finding["severity"] = "high"
            finding["problems"].append("missing_alt")
            finding["hint"] = "Add meaningful alt text describing the image's purpose."
            issues.append(finding)
            continue

        alt_n = norm(str(alt))
        if alt_n == "":
            empty += 1
            if not (decorative and allow_decorative_empty):
                finding["severity"] = "high"
                finding["problems"].append("empty_alt_not_decorative")
                finding["hint"] = "Provide alt text unless the image is purely decorative."
                issues.append(finding)
            continue

        # Now non-empty
        if len(alt_n) < min_len:
            finding["severity"] = "medium"
            finding["problems"].append("alt_too_short")
        if len(alt_n) > max_len:
            finding["severity"] = "medium"
            finding["problems"].append("alt_too_long")
        if is_generic(alt_n):
            finding["severity"] = "medium"
            finding["problems"].append("alt_generic")

        if finding["problems"]:
            finding["hint"] = "Make alt text specific and concise; avoid file names and generic words."
            issues.append(finding)
        else:
            ok += 1

    summary = {
        "total_images": total,
        "with_ok_alt": ok,
        "missing_alt": missing,
        "empty_alt": empty,
        "issue_count": len(issues),
        "coverage_ok_pct": round((ok / total) * 100.0, 1) if total else 0.0,
    }

    # sort issues: high then medium
    sev_rank = {"high": 0, "medium": 1, "ok": 2}
    issues.sort(key=lambda x: (sev_rank.get(x["severity"], 9), str(x.get("page")), str(x.get("src"))))

    return {"summary": summary, "issues": issues, "policy": {"min_len": min_len, "max_len": max_len, "allow_decorative_empty": allow_decorative_empty}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True, help="Input images JSON")
    ap.add_argument("--out", required=True, help="Output report JSON")
    ap.add_argument("--min-len", type=int, default=5)
    ap.add_argument("--max-len", type=int, default=140)
    ap.add_argument("--no-decorative-empty", action="store_true")
    args = ap.parse_args()

    with open(args.images, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError("images input must be a list")

    policy = {
        "min_len": args.min_len,
        "max_len": args.max_len,
        "allow_decorative_empty": not bool(args.no_decorative_empty),
    }

    report = audit(records, policy)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote audit to {args.out}")


if __name__ == "__main__":
    main()
