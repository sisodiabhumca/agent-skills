#!/usr/bin/env python3

import argparse
import json
from typing import Any, Dict, List, Tuple


def _as_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []


def _classify_change(change: Dict[str, Any]) -> Tuple[str, str]:
    """Return (bucket, label) where bucket in breaking|behavioral|non_breaking|deprecation|needs_review."""
    ctype = (change.get("type") or "").lower().strip()
    detail = (change.get("detail") or "").strip()

    if ctype in {"endpoint_removed", "field_removed", "required_added"}:
        return "breaking", "Breaking"

    if ctype in {"endpoint_added", "field_added", "optional_added"}:
        return "non_breaking", "Non-breaking"

    if ctype in {"type_changed", "required_changed", "behavior_changed", "response_changed"}:
        return "behavioral", "Behavioral"

    if ctype in {"deprecated", "deprecation"}:
        return "deprecation", "Deprecation"

    # fallback heuristic
    dlow = detail.lower()
    if "remove" in dlow or "no longer" in dlow:
        return "breaking", "Breaking"
    if "deprecated" in dlow:
        return "deprecation", "Deprecation"
    if "default" in dlow or "behavior" in dlow:
        return "behavioral", "Behavioral"

    return "needs_review", "Needs review"


def _fmt_item(change: Dict[str, Any]) -> str:
    target = str(change.get("target") or "(unspecified)")
    detail = str(change.get("detail") or "")
    mig = str(change.get("migration") or "")
    line = f"- **{target}**: {detail}".rstrip()
    if mig.strip():
        line += f" (Migration: {mig.strip()})"
    return line


def summarize(diff: Dict[str, Any]) -> str:
    meta = diff.get("meta", {}) if isinstance(diff.get("meta", {}), dict) else {}
    version = meta.get("version") or "(unspecified)"
    date = meta.get("date") or "(unspecified)"
    title = meta.get("title") or "API Changelog"

    changes = _as_list(diff.get("changes"))

    buckets: Dict[str, List[Dict[str, Any]]] = {
        "breaking": [],
        "behavioral": [],
        "non_breaking": [],
        "deprecation": [],
        "needs_review": [],
    }

    for ch in changes:
        if not isinstance(ch, dict):
            continue
        bucket, _label = _classify_change(ch)
        buckets[bucket].append(ch)

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- Version: {version}")
    lines.append(f"- Date: {date}")
    lines.append("")

    def section(h: str, key: str) -> None:
        lines.append(f"## {h}")
        if buckets[key]:
            for item in buckets[key]:
                lines.append(_fmt_item(item))
        else:
            lines.append("- (none)")
        lines.append("")

    section("Breaking changes", "breaking")
    section("Behavioral changes", "behavioral")
    section("Non-breaking changes", "non_breaking")
    section("Deprecations", "deprecation")

    if buckets["needs_review"]:
        section("Needs review", "needs_review")

    # Migration notes: collect unique migration strings.
    migs = []
    for key in ["breaking", "behavioral", "non_breaking", "deprecation", "needs_review"]:
        for ch in buckets[key]:
            mig = ch.get("migration")
            if isinstance(mig, str) and mig.strip():
                migs.append(mig.strip())

    lines.append("## Migration notes")
    if migs:
        for m in sorted(set(migs)):
            lines.append(f"- {m}")
    else:
        lines.append("- (no migration notes provided)")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize an API diff JSON into a Markdown changelog")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        diff = json.load(f)

    if not isinstance(diff, dict):
        raise SystemExit("Input must be a JSON object")

    md = summarize(diff)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
