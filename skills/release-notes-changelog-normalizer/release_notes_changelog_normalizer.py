#!/usr/bin/env python3
"""Vendor-neutral release notes -> changelog normalizer (stdlib-only)."""

import argparse
import json
import re
from typing import Any, Dict, List


CATEGORIES = [
    "Added",
    "Changed",
    "Deprecated",
    "Removed",
    "Fixed",
    "Security",
]

KEYWORDS = {
    "Security": ["cve", "vulnerability", "security", "xss", "csrf", "auth"],
    "Fixed": ["fix", "fixed", "bug", "resolve", "patch"],
    "Added": ["add", "added", "introduce", "new", "support"],
    "Removed": ["remove", "removed", "delete", "drop"],
    "Deprecated": ["deprecat", "sunset"],
    "Changed": ["change", "changed", "update", "improve", "optimiz", "refactor"],
}


def normalize_line(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^[\-*\s]+", "", s)
    s = re.sub(r"\s+", " ", s)
    if not s:
        return ""
    # sentence case (light)
    s = s[0].upper() + s[1:]
    if s[-1] not in ".!?":
        s += "."
    return s


def categorize(s: str) -> str:
    t = s.lower()
    for cat in CATEGORIES:
        for kw in KEYWORDS.get(cat, []):
            if kw in t:
                return cat
    return "Changed"


def build_entry(payload: Dict[str, Any]) -> str:
    version = str(payload.get("version", "Unreleased")).strip() or "Unreleased"
    date = str(payload.get("date", "")).strip()
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise ValueError("items must be a list")

    seen = set()
    grouped: Dict[str, List[str]] = {c: [] for c in CATEGORIES}

    for raw in items:
        line = normalize_line(str(raw))
        if not line:
            continue
        key = line.lower()
        if key in seen:
            continue
        seen.add(key)
        cat = categorize(line)
        grouped[cat].append(line)

    header = f"## [{version}]" + (f" - {date}" if date else "")
    out = [header, ""]
    for cat in CATEGORIES:
        if grouped[cat]:
            out.append(f"### {cat}")
            for line in grouped[cat]:
                out.append(f"- {line}")
            out.append("")

    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input release notes JSON")
    ap.add_argument("--out", required=True, help="Output markdown file")
    args = ap.parse_args()

    with open(args.inp, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError("Input must be an object")

    md = build_entry(payload)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote changelog entry to {args.out}")


if __name__ == "__main__":
    main()
