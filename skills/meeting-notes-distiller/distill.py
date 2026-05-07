"""Meeting Notes Distiller.

Reads a transcript or raw notes and emits a structured Markdown summary.

Usage:
  python distill.py --in transcript.txt --attendees "Alex,Priya,Marcus"
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path


SPEAKER_RE = re.compile(r"^([A-Z][a-zA-Z .'-]{1,40}):\s+")
TIMESTAMP_RE = re.compile(r"^\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?\s*$|-->")
VTT_HEADER_RE = re.compile(r"^WEBVTT", re.IGNORECASE)

ACTION_VERBS = [
    "will", "should", "needs to", "owns", "to do", "action", "let's", "let us",
    "follow up", "follow-up", "send", "share", "draft", "write", "review",
    "schedule", "set up", "create", "add", "open", "file", "ping", "check",
]
DECISION_HINTS = [
    r"\bdecided\b", r"\bagreed\b", r"\bwe('?| are) going to\b", r"\bdecision\b",
    r"\bsigned off\b", r"\bapproved\b",
]
RISK_HINTS = [
    r"\brisk\b", r"\bblocker\b", r"\bblocked by\b", r"\bconcern\b",
    r"\bdepend(s|ent) on\b", r"\bif .* doesn'?t\b", r"\bworried\b",
]
QUESTION_HINTS = [r"\?$", r"\bopen question\b", r"\bunclear\b", r"\bTBD\b"]

DUE_PATTERNS = [
    (re.compile(r"\bby\s+(?P<d>(?:tomorrow|today|tonight|monday|tuesday|wednesday|thursday|friday|saturday|sunday|next week|end of week|EOW|EOD|end of day|next month))\b", re.IGNORECASE), "phrase"),
    (re.compile(r"\bby\s+(?P<d>\d{4}-\d{2}-\d{2})\b"), "date"),
    (re.compile(r"\bby\s+(?P<d>\w+ \d{1,2}(?:,\s*\d{4})?)\b"), "longdate"),
    (re.compile(r"\bdue\s+(?P<d>\d{4}-\d{2}-\d{2})\b"), "date"),
]


@dataclass
class Line:
    idx: int
    speaker: str
    text: str


@dataclass
class ActionItem:
    text: str
    owner: str = "(unowned)"
    due: str = ""
    source_line: int = 0


def clean_lines(text: str) -> list[Line]:
    out: list[Line] = []
    for i, raw in enumerate(text.splitlines(), 1):
        s = raw.strip()
        if not s or VTT_HEADER_RE.match(s) or TIMESTAMP_RE.match(s) or s.isdigit():
            continue
        m = SPEAKER_RE.match(s)
        speaker = ""
        if m:
            speaker = m.group(1)
            s = s[m.end():].strip()
        # split on sentence boundaries to preserve granularity
        for sent in re.split(r"(?<=[.!?])\s+", s):
            sent = sent.strip()
            if sent:
                out.append(Line(idx=i, speaker=speaker, text=sent))
    return out


def normalize_due(text: str) -> str:
    today = date.today()
    for pat, kind in DUE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        raw = m.group("d").strip()
        low = raw.lower()
        if kind == "phrase":
            mapping = {
                "today": today,
                "tonight": today,
                "tomorrow": today + timedelta(days=1),
                "eod": today,
                "end of day": today,
                "eow": today + timedelta(days=(4 - today.weekday()) % 7 or 7),
                "end of week": today + timedelta(days=(4 - today.weekday()) % 7 or 7),
                "next week": today + timedelta(days=7),
                "next month": today + timedelta(days=30),
            }
            if low in mapping:
                return mapping[low].isoformat()
            weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            if low in weekdays:
                target = weekdays.index(low)
                delta = (target - today.weekday()) % 7
                return (today + timedelta(days=delta or 7)).isoformat()
        if kind == "date":
            try:
                return datetime.fromisoformat(raw).date().isoformat()
            except Exception:
                pass
        if kind == "longdate":
            for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d", "%b %d"):
                try:
                    d = datetime.strptime(raw, fmt).date()
                    if d.year == 1900:
                        d = d.replace(year=today.year)
                    return d.isoformat()
                except Exception:
                    continue
        return raw
    return ""


def attribute_owner(line_text: str, attendees: list[str]) -> str:
    low = line_text.lower()
    for name in attendees:
        if not name:
            continue
        if re.search(rf"\b{re.escape(name.lower())}\b", low):
            return name
    m = re.search(r"@([A-Za-z][A-Za-z._-]{1,30})", line_text)
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z][a-z]+) (?:will|to|owns|is going to)\b", line_text)
    if m:
        return m.group(1)
    return "(unowned)"


def extract(lines: list[Line], attendees: list[str]) -> dict:
    actions: list[ActionItem] = []
    decisions: list[tuple[int, str]] = []
    risks: list[tuple[int, str]] = []
    questions: list[tuple[int, str]] = []

    for ln in lines:
        text = ln.text
        low = text.lower()
        if any(verb in low for verb in ACTION_VERBS) and re.search(r"\b(will|to|by|owns|let'?s|should)\b", low):
            owner = ln.speaker if ln.speaker else attribute_owner(text, attendees)
            owner = owner if owner else attribute_owner(text, attendees)
            actions.append(ActionItem(text=text, owner=owner or "(unowned)", due=normalize_due(text), source_line=ln.idx))
        if any(re.search(p, low) for p in DECISION_HINTS):
            decisions.append((ln.idx, text))
        if any(re.search(p, low) for p in RISK_HINTS):
            risks.append((ln.idx, text))
        if any(re.search(p, text, re.IGNORECASE) for p in QUESTION_HINTS):
            questions.append((ln.idx, text))

    # de-dupe
    actions = _dedupe(actions, key=lambda a: a.text)
    return {"actions": actions, "decisions": decisions, "risks": risks, "questions": questions}


def _dedupe(items, key):
    seen = set()
    out = []
    for x in items:
        k = key(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def render(meta: dict, attendees: list[str], purpose: str, ext: dict, lines: list[Line]) -> str:
    n_lines = len(lines)
    out = [
        "# Meeting Notes",
        "",
        f"- **Purpose:** {purpose or '_(not specified)_'}",
        f"- **Attendees:** {', '.join(attendees) if attendees else '_(not specified)_'}",
        f"- **Lines processed:** {n_lines}",
        "",
        "## Summary",
    ]
    summary_seed = " ".join(l.text for l in lines[:6])
    out.append(summary_seed if summary_seed else "_(empty)_")

    out += ["", "## Decisions"]
    for idx, txt in ext["decisions"][:20]:
        out.append(f"- _\"{txt}\"_ (line {idx})")
    if not ext["decisions"]:
        out.append("- (none detected)")

    out += ["", "## Action items",
            "| # | Action | Owner | Due | Source line |",
            "|---|---|---|---|---|"]
    for i, a in enumerate(ext["actions"], 1):
        out.append(f"| {i} | {a.text} | {a.owner} | {a.due or '—'} | {a.source_line} |")
    if not ext["actions"]:
        out.append("| — | (none detected) | — | — | — |")

    unowned = [a for a in ext["actions"] if a.owner == "(unowned)"]
    if unowned:
        out += ["", f"> ⚠️ {len(unowned)} action items have no owner — assign before sending."]

    out += ["", "## Risks / blockers"]
    for idx, txt in ext["risks"][:20]:
        out.append(f"- _\"{txt}\"_ (line {idx})")
    if not ext["risks"]:
        out.append("- (none detected)")

    out += ["", "## Open questions"]
    for idx, txt in ext["questions"][:20]:
        out.append(f"- _\"{txt}\"_ (line {idx})")
    if not ext["questions"]:
        out.append("- (none detected)")

    out += ["", "## Follow-up email (draft)", ""]
    out.append("Subject: Notes & action items — " + (purpose or "today's meeting"))
    out.append("")
    out.append(f"Hi all,")
    out.append("")
    recap = purpose if purpose else "today's meeting"
    out.append(f"Quick recap of {recap}:")
    if ext["decisions"]:
        out.append("")
        out.append("Decisions:")
        for _, t in ext["decisions"][:5]:
            out.append(f"- {t}")
    if ext["actions"]:
        out.append("")
        out.append("Action items:")
        for a in ext["actions"]:
            due = f" (due {a.due})" if a.due else ""
            out.append(f"- {a.owner}: {a.text}{due}")
    if ext["risks"]:
        out.append("")
        out.append("Risks / blockers:")
        for _, t in ext["risks"][:5]:
            out.append(f"- {t}")
    out.append("")
    out.append("Let me know if anything is wrong or missing.")
    out.append("")
    out.append("Thanks!")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", required=True, help="Path to transcript / notes, or - for stdin")
    ap.add_argument("--attendees", default="", help="Comma-separated attendee names")
    ap.add_argument("--purpose", default="")
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    text = sys.stdin.read() if args.inp == "-" else Path(args.inp).read_text(errors="ignore")
    attendees = [a.strip() for a in args.attendees.split(",") if a.strip()]
    lines = clean_lines(text)
    ext = extract(lines, attendees)
    body = render({}, attendees, args.purpose, ext, lines)
    if args.out == "-":
        print(body)
    else:
        Path(args.out).write_text(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
