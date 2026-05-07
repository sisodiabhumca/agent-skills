"""Release notes writer.

Reads merged PRs from CSV or JSON and emits sectioned release notes plus a Slack TL;DR.

Usage:
    python generate.py --prs sample_prs.csv --version 3.2.0 --date 2025-05-07
    python generate.py --prs sample_prs.json --audience internal --version 3.2.0
    python generate.py --git-range v1.4.0..HEAD --version 1.5.0   # reads git log

Vendor-neutral. Stdlib only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

CATEGORIES = ["Breaking", "Feature", "Improvement", "Fix", "Internal"]

INTERNAL_LABELS = {"chore", "ci", "internal", "infra", "dependencies", "deps", "test", "tests", "refactor"}
FEATURE_LABELS = {"feature", "feat", "enhancement"}
FIX_LABELS = {"fix", "bug", "bugfix"}
IMPROVEMENT_LABELS = {"improvement", "perf", "performance", "polish", "ux"}
BREAKING_LABELS = {"breaking", "breaking-change", "major"}


@dataclass
class Change:
    number: str
    title: str
    body: str = ""
    labels: list[str] = field(default_factory=list)
    author: str = ""
    url: str = ""
    category: str = "Improvement"

    @property
    def link(self) -> str:
        if self.url:
            return f"[#{self.number}]({self.url})"
        return f"#{self.number}"


def normalize_labels(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        items = re.split(r"[;,|]", str(raw))
    return [s.strip().lower() for s in items if s and s.strip()]


def classify(c: Change) -> str:
    title = c.title.strip()
    body = c.body or ""
    labels = set(c.labels)

    # Explicit breaking signal wins
    if "BREAKING CHANGE" in body.upper() or labels & BREAKING_LABELS or re.match(r"^\w+!:", title):
        return "Breaking"

    # Conventional commit prefix
    m = re.match(r"^(\w+)(?:\([^)]+\))?:\s", title)
    if m:
        prefix = m.group(1).lower()
        if prefix == "feat":
            return "Feature"
        if prefix == "fix":
            return "Fix"
        if prefix in {"perf", "refactor", "style"}:
            return "Improvement" if prefix == "perf" else "Internal"
        if prefix in {"chore", "ci", "build", "test", "docs"}:
            return "Internal"

    if labels & FEATURE_LABELS:
        return "Feature"
    if labels & FIX_LABELS:
        return "Fix"
    if labels & IMPROVEMENT_LABELS:
        return "Improvement"
    if labels & INTERNAL_LABELS:
        return "Internal"

    # Heuristic on verbs
    lower = title.lower()
    if any(lower.startswith(v) for v in ("add ", "introduce ", "support ", "enable ")):
        return "Feature"
    if any(lower.startswith(v) for v in ("fix ", "resolve ", "patch ", "correct ")):
        return "Fix"
    return "Improvement"


def load_csv(path: Path) -> list[Change]:
    out: list[Change] = []
    with path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.append(Change(
                number=str(row.get("number", "")).strip(),
                title=row.get("title", "").strip(),
                body=row.get("body", "") or "",
                labels=normalize_labels(row.get("labels")),
                author=row.get("author", "").strip(),
                url=row.get("url", "").strip(),
            ))
    return out


def load_json(path: Path) -> list[Change]:
    data = json.loads(path.read_text())
    out = []
    for row in data:
        out.append(Change(
            number=str(row.get("number", "")),
            title=str(row.get("title", "")),
            body=str(row.get("body", "") or ""),
            labels=normalize_labels(row.get("labels")),
            author=str(row.get("author", "")),
            url=str(row.get("url", "")),
        ))
    return out


def load_git_range(rng: str) -> list[Change]:
    # Use a custom format: <hash>\x1f<subject>\x1f<body>\x1e
    fmt = "%H%x1f%s%x1f%b%x1e"
    res = subprocess.run(
        ["git", "log", rng, f"--pretty=format:{fmt}", "--no-merges"],
        check=True, capture_output=True, text=True,
    )
    out = []
    for chunk in res.stdout.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split("\x1f")
        if len(parts) < 3:
            continue
        h, subject, body = parts[0], parts[1], parts[2]
        out.append(Change(number=h[:7], title=subject, body=body))
    return out


def render_markdown(changes: list[Change], version: str, date: str, audience: str) -> str:
    by_cat: dict[str, list[Change]] = {c: [] for c in CATEGORIES}
    for ch in changes:
        by_cat[ch.category].append(ch)

    lines: list[str] = [f"# Release {version} — {date}", ""]

    breaking = by_cat["Breaking"]
    features = by_cat["Feature"]
    improvements = by_cat["Improvement"]
    fixes = by_cat["Fix"]
    internal = by_cat["Internal"]

    # Highlights = up to 3 most impactful (breaking + features)
    highlights = (breaking + features)[:3]
    if highlights:
        lines += ["## Highlights", ""]
        for h in highlights:
            lines.append(f"- {h.title} ({h.link})")
        lines.append("")

    if breaking:
        lines += ["## Breaking changes", ""]
        for ch in breaking:
            lines.append(f"- **{ch.title}** ({ch.link})")
            if ch.body:
                first = ch.body.strip().splitlines()[0]
                lines.append(f"  - Migration: {first}")
        lines.append("")

    if features:
        lines += ["## New features", ""]
        for ch in features:
            lines.append(f"- {ch.title} ({ch.link})")
        lines.append("")

    if improvements:
        lines += ["## Improvements", ""]
        for ch in improvements:
            lines.append(f"- {ch.title} ({ch.link})")
        lines.append("")

    if fixes:
        lines += ["## Bug fixes", ""]
        for ch in fixes:
            lines.append(f"- {ch.title} ({ch.link})")
        lines.append("")

    if audience == "internal" and internal:
        lines += ["## Internal", ""]
        for ch in internal:
            lines.append(f"- {ch.title} ({ch.link})")
        lines.append("")
    elif internal:
        lines += [f"<!-- {len(internal)} internal item(s) omitted from public notes -->", ""]

    return "\n".join(lines).rstrip() + "\n"


def render_slack(changes: list[Change], version: str) -> str:
    by_cat: dict[str, list[Change]] = {c: [] for c in CATEGORIES}
    for ch in changes:
        by_cat[ch.category].append(ch)
    bullets: list[str] = []
    if by_cat["Breaking"]:
        bullets.append(f":warning: *Breaking:* {by_cat['Breaking'][0].title}")
    if by_cat["Feature"]:
        bullets.append(f":sparkles: *New:* {by_cat['Feature'][0].title}")
    if by_cat["Fix"]:
        bullets.append(f":wrench: *Fixed:* {by_cat['Fix'][0].title}")
    while len(bullets) < 3 and by_cat["Improvement"]:
        bullets.append(f":arrow_up: {by_cat['Improvement'].pop(0).title}")
    bullets = bullets[:3] or ["(no public-facing changes)"]
    return f"*Release {version}*\n" + "\n".join(f"• {b}" for b in bullets) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--prs", help="Path to merged PRs CSV or JSON")
    src.add_argument("--git-range", help="git log range, e.g. v1.4.0..HEAD")
    p.add_argument("--version", required=True)
    p.add_argument("--date", default="")
    p.add_argument("--audience", choices=["public", "internal"], default="public")
    p.add_argument("--out-md", default="RELEASE_NOTES.md")
    p.add_argument("--out-slack", default="SLACK.md")
    args = p.parse_args(argv)

    if args.prs:
        path = Path(args.prs)
        if path.suffix.lower() == ".json":
            changes = load_json(path)
        else:
            changes = load_csv(path)
    else:
        changes = load_git_range(args.git_range)

    for ch in changes:
        ch.category = classify(ch)

    if args.audience == "public":
        public_changes = [c for c in changes if c.category != "Internal"]
    else:
        public_changes = changes

    # Pass full list for internal-only rendering when audience=internal
    md = render_markdown(changes if args.audience == "internal" else changes, args.version, args.date or "", args.audience)
    slack = render_slack(public_changes, args.version)

    Path(args.out_md).write_text(md)
    Path(args.out_slack).write_text(slack)

    counts = {cat: sum(1 for c in changes if c.category == cat) for cat in CATEGORIES}
    print(f"Wrote {args.out_md} and {args.out_slack}")
    print("Counts:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
