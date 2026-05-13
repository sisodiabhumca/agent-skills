#!/usr/bin/env python3
"""Vendor-neutral meeting action item extractor.

Heuristic extraction of action items from a plain-text transcript.
Stdlib-only.
"""

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


CUE_PATTERNS = [
    re.compile(r"\baction item\b", re.I),
    re.compile(r"\bai:\b", re.I),
    re.compile(r"\btodo\b", re.I),
    re.compile(r"\bwe should\b", re.I),
    re.compile(r"\bi will\b", re.I),
    re.compile(r"\bi'll\b", re.I),
    re.compile(r"\bcan you\b", re.I),
]

SPEAKER_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 _\-]{0,30}):\s*(.*)$")

DUE_ISO_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
DUE_BY_DAY_RE = re.compile(r"\bby\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)


def load_participants(path: Optional[str]) -> List[str]:
    if not path:
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    return [str(x) for x in data]


def next_weekday(today: date, weekday: int) -> date:
    # weekday: Monday=0
    days_ahead = (weekday - today.weekday() + 7) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def parse_due(text: str, today: Optional[date] = None) -> Optional[str]:
    today = today or date.today()
    m = DUE_ISO_RE.search(text)
    if m:
        return m.group(1)

    m = DUE_BY_DAY_RE.search(text)
    if m:
        day = m.group(1).lower()
        mapping = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        d = next_weekday(today, mapping[day])
        return d.isoformat()

    return None


def looks_like_action(line: str) -> bool:
    return any(p.search(line) for p in CUE_PATTERNS)


def normalize_task(text: str) -> str:
    t = text.strip()
    t = re.sub(r"\b(action item|ai:|todo)\b\s*:?", "", t, flags=re.I).strip()
    # remove leading fillers
    t = re.sub(r"^(we should|can you|i will|i'll)\s+", "", t, flags=re.I).strip()
    t = re.sub(r"\s+", " ", t)
    return t


def infer_owner(speaker: Optional[str], line: str, participants: List[str]) -> Optional[str]:
    if speaker:
        return speaker.strip()
    # try match participant names in line
    for p in participants:
        if re.search(r"\b" + re.escape(p) + r"\b", line, flags=re.I):
            return p
    return None


def dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = re.sub(r"\W+", "", (it.get("task") or "").lower())[:80]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--participants")
    ap.add_argument("--out")
    args = ap.parse_args()

    participants = load_participants(args.participants)

    with open(args.transcript, "r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]

    action_items: List[Dict[str, Any]] = []
    notes: List[str] = []

    for ln in lines:
        speaker = None
        content = ln
        m = SPEAKER_RE.match(ln)
        if m:
            speaker = m.group(1)
            content = m.group(2)

        if not looks_like_action(content):
            continue

        task = normalize_task(content)
        if not task:
            continue

        due = parse_due(content)
        owner = infer_owner(speaker, content, participants)

        if owner is None:
            notes.append(f"Owner unknown for: {ln}")
        if due is None:
            notes.append(f"Due date unknown for: {ln}")

        action_items.append(
            {
                "task": task,
                "owner": owner,
                "due_date": due,
                "evidence": ln.strip(),
            }
        )

    action_items = dedupe(action_items)

    report = {"action_items": action_items, "notes": notes}

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
