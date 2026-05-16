#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


DECISION_PATTERNS = [
    re.compile(r"\b(decided|decision|approved|agree(d)?|we will|let's)\b", re.I),
]
ACTION_PATTERNS = [
    re.compile(r"\b(action item|action:|todo|to-do|owner:)\b", re.I),
    re.compile(r"\b(follow up|please|can you)\b", re.I),
]

DUE_RE = re.compile(
    r"\b(by|before)\s+(\d{4}-\d{2}-\d{2}|next\s+week|tomorrow|eow|end\s+of\s+week)\b",
    re.I,
)

SPEAKER_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9_ -]{0,30}):\s+(.*)$")


@dataclass
class Extracted:
    kind: str  # decision|action
    text: str
    speaker: Optional[str]
    due: Optional[str]
    uncertain: bool
    line_no: int


def _norm(s: str) -> str:
    return " ".join(s.strip().split())


def _extract_owner(text: str, speaker: Optional[str]) -> Tuple[Optional[str], bool]:
    m = re.search(r"\bowner:\s*([A-Za-z][A-Za-z0-9_ -]{0,30})\b", text, re.I)
    if m:
        return _norm(m.group(1)), False
    # If it says "I will" assume speaker is owner.
    if speaker and re.search(r"\b(i will|i'll)\b", text, re.I):
        return speaker, False
    return speaker, True if speaker else True


def _extract_due(text: str) -> Tuple[Optional[str], bool]:
    m = DUE_RE.search(text)
    if m:
        return _norm(m.group(2)), False
    return None, True


def extract(transcript: str) -> List[Extracted]:
    items: List[Extracted] = []
    lines = transcript.splitlines()

    for i, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue

        speaker = None
        content = line
        sm = SPEAKER_RE.match(line)
        if sm:
            speaker = _norm(sm.group(1))
            content = sm.group(2)

        content_n = _norm(content)

        is_decision = any(p.search(content_n) for p in DECISION_PATTERNS)
        is_action = any(p.search(content_n) for p in ACTION_PATTERNS)

        if not (is_decision or is_action):
            continue

        due, due_uncertain = _extract_due(content_n)
        owner, owner_uncertain = _extract_owner(content_n, speaker)

        kind = "decision" if is_decision and not is_action else ("action" if is_action else "decision")
        uncertain = owner_uncertain and due_uncertain

        items.append(
            Extracted(
                kind=kind,
                text=content_n,
                speaker=speaker,
                due=due,
                uncertain=uncertain,
                line_no=i,
            )
        )

    return items


def render_md(items: List[Extracted]) -> str:
    decisions = [x for x in items if x.kind == "decision"]
    actions = [x for x in items if x.kind == "action"]

    lines: List[str] = []
    lines.append("# Meeting decision log")
    lines.append("")

    lines.append("## Decisions")
    lines.append("| ID | Decision (verbatim) | Mentioned by | Notes |")
    lines.append("|---|---|---|---|")
    if not decisions:
        lines.append("| (none) | (n/a) | (n/a) | (n/a) |")
    else:
        for idx, d in enumerate(decisions, start=1):
            note = f"line {d.line_no}" + ("; uncertain" if d.uncertain else "")
            lines.append(
                f"| D{idx} | {d.text} | {d.speaker or '(unknown)'} | {note} |"
            )
    lines.append("")

    lines.append("## Action items")
    lines.append("| ID | Action (verbatim) | Owner | Due date | Notes |")
    lines.append("|---|---|---|---|---|")
    if not actions:
        lines.append("| (none) | (n/a) | (n/a) | (n/a) | (n/a) |")
    else:
        for idx, a in enumerate(actions, start=1):
            owner = a.speaker or "(unassigned)"
            due = a.due or "(unspecified)"
            note = f"line {a.line_no}" + ("; uncertain" if a.uncertain else "")
            lines.append(f"| A{idx} | {a.text} | {owner} | {due} | {note} |")

    uncertain = [x for x in items if x.uncertain]
    if uncertain:
        lines.append("")
        lines.append("## Uncertain extractions")
        for u in uncertain:
            lines.append(f"- line {u.line_no}: {u.text}")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract meeting decisions and action items from a transcript")
    ap.add_argument("--input", required=True, help="Transcript .txt")
    ap.add_argument("--output", required=True, help="Output Markdown path")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        transcript = f.read()

    items = extract(transcript)
    md = render_md(items)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
