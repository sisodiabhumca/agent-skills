#!/usr/bin/env python3
import argparse
import json
import re
from typing import Any, Dict, List, Optional, Tuple

ACTION_PATTERNS = [
    re.compile(r"\baction\s*:\s*(.+)$", re.IGNORECASE),
    re.compile(r"\btodo\s*:\s*(.+)$", re.IGNORECASE),
    re.compile(r"\bcan you\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bwe should\s+(.+)$", re.IGNORECASE),
    re.compile(r"\bi(?:\s+will|'ll)\s+(.+)$", re.IGNORECASE),
]

DECISION_PATTERNS = [
    re.compile(r"\bdecision\s*:\s*(.+)$", re.IGNORECASE),
    re.compile(r"\bwe decided\b\s*(.+)$", re.IGNORECASE),
    re.compile(r"\bwe agree(?:d)?\b\s*(.+)$", re.IGNORECASE),
]

SPEAKER_RE = re.compile(r"^([A-Za-z][A-Za-z\-\s]{1,40}):\s+(.*)$")


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    decisions: List[str] = []
    actions: List[Dict[str, Any]] = []

    with open(args.input, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip("\n")
            if not line.strip():
                continue

            owner = None
            content = line
            m = SPEAKER_RE.match(line)
            if m:
                owner = normalize_whitespace(m.group(1))
                content = m.group(2)

            c = normalize_whitespace(content)

            for dp in DECISION_PATTERNS:
                dm = dp.search(c)
                if dm:
                    decisions.append(normalize_whitespace(dm.group(1) or ""))
                    break

            for apx in ACTION_PATTERNS:
                am = apx.search(c)
                if am:
                    task = normalize_whitespace(am.group(1) or "")
                    if task:
                        # if pattern isn't first-person, avoid attributing owner incorrectly
                        inferred_owner = owner
                        if apx.pattern.lower().startswith("\\bcan you"):
                            inferred_owner = None
                        actions.append({
                            "owner": inferred_owner,
                            "task": task,
                            "evidence_line": line.strip(),
                        })
                    break

    report = {
        "decisions": [d for d in decisions if d],
        "action_items": actions,
        "stats": {"decisions": len([d for d in decisions if d]), "action_items": len(actions)},
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
