#!/usr/bin/env python3
"""api-changelog-impact-analyzer

Heuristically analyzes an API changelog (markdown/text) and flags potentially breaking changes.
Optionally cross-checks with a client-usage JSON file listing endpoints/fields used.

stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


BREAKING_HINTS = [
    "removed",
    "removal",
    "delete",
    "deleted",
    "renamed",
    "rename",
    "no longer",
    "deprecated and will be removed",
    "required",
    "must",
    "breaking",
    "authentication",
    "authorization",
    "scope",
    "permission",
]

DEPRECATION_HINTS = ["deprecated", "sunset", "end of life", "eol"]
BEHAVIOR_HINTS = ["default", "changed", "now returns", "behavior", "limit", "rate", "ordering", "pagination"]

ENDPOINT_RE = re.compile(r"\b/([a-zA-Z0-9_\-]+/)*[a-zA-Z0-9_\-]+\b")
FIELD_RE = re.compile(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b")


@dataclass
class Item:
    text: str
    category: str
    endpoints: List[str]
    fields: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "category": self.category,
            "endpoints": self.endpoints,
            "fields": self.fields,
        }


def _extract_bullets(text: str) -> List[str]:
    lines = text.splitlines()
    bullets: List[str] = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("- ") or s.startswith("* "):
            bullets.append(s[2:].strip())
    # If no bullets, fall back to sentences-ish blocks
    if not bullets:
        chunks = [c.strip() for c in re.split(r"\n\n+", text) if c.strip()]
        bullets = chunks
    return bullets


def _classify(t: str) -> str:
    low = t.lower()
    if any(h in low for h in BREAKING_HINTS):
        return "breaking"
    if any(h in low for h in DEPRECATION_HINTS):
        return "deprecation"
    if any(h in low for h in BEHAVIOR_HINTS):
        return "behavior_change"
    return "additive"


def _extract_endpoints(t: str) -> List[str]:
    eps = sorted(set(m.group(0) for m in ENDPOINT_RE.finditer(t)))
    # Filter obvious markdown paths like /tmp
    return [e for e in eps if not e.startswith("/tmp")]


def _extract_fields(t: str) -> List[str]:
    # Heuristic: pick code-ish tokens, filter stopwords
    stop = {
        "the",
        "and",
        "or",
        "to",
        "a",
        "an",
        "of",
        "in",
        "on",
        "for",
        "with",
        "now",
        "new",
        "added",
        "removed",
        "deprecated",
        "will",
        "be",
        "is",
        "are",
        "as",
    }
    toks = [m.group(0) for m in FIELD_RE.finditer(t)]
    toks2 = [x for x in toks if x.lower() not in stop and len(x) >= 3]
    # Limit to avoid noise
    return sorted(set(toks2))[:25]


def analyze(changelog_text: str, client_usage: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    bullets = _extract_bullets(changelog_text)
    items: List[Item] = []
    for b in bullets:
        cat = _classify(b)
        items.append(Item(text=b, category=cat, endpoints=_extract_endpoints(b), fields=_extract_fields(b)))

    used_endpoints: Set[str] = set()
    used_fields: Set[str] = set()
    if client_usage:
        for e in client_usage.get("endpoints", []) or []:
            if isinstance(e, str):
                used_endpoints.add(e)
        for f in client_usage.get("fields", []) or []:
            if isinstance(f, str):
                used_fields.add(f)

    overlaps: List[Dict[str, Any]] = []
    if client_usage:
        for it in items:
            hit_eps = sorted(set(it.endpoints) & used_endpoints)
            hit_fields = sorted(set(it.fields) & used_fields)
            if hit_eps or hit_fields:
                overlaps.append(
                    {
                        "text": it.text,
                        "category": it.category,
                        "matching_endpoints": hit_eps,
                        "matching_fields": hit_fields,
                    }
                )

    by_cat: Dict[str, List[Dict[str, Any]]] = {"breaking": [], "deprecation": [], "behavior_change": [], "additive": []}
    for it in items:
        by_cat[it.category].append(it.to_dict())

    return {
        "summary": {
            "total_items": len(items),
            "breaking": len(by_cat["breaking"]),
            "deprecation": len(by_cat["deprecation"]),
            "behavior_change": len(by_cat["behavior_change"]),
            "additive": len(by_cat["additive"]),
            "overlaps": len(overlaps),
        },
        "items": by_cat,
        "overlaps": overlaps,
    }


def format_markdown(report: Dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        "# API changelog impact analysis\n",
        f"Items: {s['total_items']} (breaking: {s['breaking']}, deprecation: {s['deprecation']}, behavior: {s['behavior_change']}, additive: {s['additive']})\n",
    ]

    def _section(title: str, key: str) -> None:
        lines.append(f"## {title}\n")
        rows = report["items"][key]
        if not rows:
            lines.append("- None\n")
            return
        for r in rows:
            extras = []
            if r.get("endpoints"):
                extras.append("endpoints: " + ", ".join(r["endpoints"]))
            if r.get("fields"):
                extras.append("tokens: " + ", ".join(r["fields"]))
            suffix = (" (" + "; ".join(extras) + ")") if extras else ""
            lines.append(f"- {r['text']}{suffix}")
        lines.append("")

    _section("Breaking", "breaking")
    _section("Deprecations", "deprecation")
    _section("Behavior changes", "behavior_change")
    _section("Additive", "additive")

    if report.get("overlaps"):
        lines.append("## Overlaps with client usage\n")
        for o in report["overlaps"]:
            bits = []
            if o.get("matching_endpoints"):
                bits.append("endpoints: " + ", ".join(o["matching_endpoints"]))
            if o.get("matching_fields"):
                bits.append("fields: " + ", ".join(o["matching_fields"]))
            lines.append(f"- **{o['category']}**: {o['text']} ({'; '.join(bits)})")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Analyze an API changelog and flag potential breaking changes.")
    ap.add_argument("--changelog", required=True, help="Path to changelog markdown/text")
    ap.add_argument("--client-usage", default=None, help="Optional path to client usage JSON")
    ap.add_argument("--json-out", default=None, help="Optional path to write JSON report")
    args = ap.parse_args(argv)

    with open(args.changelog, "r", encoding="utf-8") as f:
        changelog_text = f.read()

    client_usage = None
    if args.client_usage:
        with open(args.client_usage, "r", encoding="utf-8") as f:
            client_usage = json.load(f)

    report = analyze(changelog_text, client_usage=client_usage)
    print(format_markdown(report))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
