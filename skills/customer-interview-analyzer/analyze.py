"""Customer Interview Analyzer.

Reads a folder of interview transcripts (.txt/.md/.vtt) and produces a Markdown
research report with themes, frequencies, and verbatim quotes.

Usage:
  python analyze.py --dir ./transcripts --question "Why do users churn?"
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

STOPWORDS = set(
    """a an the and or but so if then than that this these those is are was were be been being
    have has had do does did of in on at by to for from with as it its i you we they he she them
    me my your our their not no yes ok okay just like really very kind sort thing things stuff
    um uh you know mean i'm i've i'd it's that's there's we're they're we've don't can't won't
    just so really like kind of sort of i think i feel maybe sometimes always never get got"""
    .split()
)
PAIN_HINTS = [
    "frustrat", "annoy", "hate", "confus", "can't", "cannot", "broken", "slow", "lost",
    "stuck", "hard to", "difficult", "wish", "should", "missing", "fails", "error", "crash",
]
JTBD_HINTS = [
    "i want to", "i need to", "trying to", "so that", "in order to", "i'm trying", "help me",
]


def read_transcripts(folder: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for p in Path(folder).rglob("*"):
        if p.suffix.lower() in {".txt", ".md", ".vtt"} and p.is_file():
            text = p.read_text(errors="ignore")
            if p.suffix.lower() == ".vtt":
                text = "\n".join(l for l in text.splitlines() if "-->" not in l and not l.strip().isdigit() and l.strip() != "WEBVTT")
            out[str(p)] = text
    return out


def sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def ngrams(tokens: list[str], n: int) -> list[str]:
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def tokenize(s: str) -> list[str]:
    s = re.sub(r"[^a-zA-Z0-9'\s]", " ", s.lower())
    toks = [t for t in s.split() if t and t not in STOPWORDS and len(t) > 2]
    return toks


def extract_themes(transcripts: dict[str, str], top_k: int = 12) -> list[tuple[str, int, list[tuple[str, str]]]]:
    """Return list of (theme, count, [(file, sentence), ...])."""
    counter: Counter[str] = Counter()
    occurrences: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for file, text in transcripts.items():
        for sent in sentences(text):
            toks = tokenize(sent)
            for n in (2, 3):
                for ng in ngrams(toks, n):
                    counter[ng] += 1
                    if len(occurrences[ng]) < 3:
                        occurrences[ng].append((file, sent))

    # filter low-info phrases
    themes = [(ph, c) for ph, c in counter.items() if c >= 2 and not all(t in STOPWORDS for t in ph.split())]
    themes.sort(key=lambda x: (-x[1], x[0]))
    out: list[tuple[str, int, list[tuple[str, str]]]] = []
    seen_terms: set[str] = set()
    for ph, c in themes:
        # dedupe themes that share core terms with already-picked themes
        core = set(ph.split()) - STOPWORDS
        if core & seen_terms and len(out) >= 3:
            continue
        out.append((ph, c, occurrences[ph]))
        seen_terms |= core
        if len(out) >= top_k:
            break
    return out


def find_pain_points(transcripts: dict[str, str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for file, text in transcripts.items():
        for sent in sentences(text):
            low = sent.lower()
            if any(h in low for h in PAIN_HINTS):
                out.append((file, sent))
    return out


def find_jtbd(transcripts: dict[str, str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for file, text in transcripts.items():
        for sent in sentences(text):
            low = sent.lower()
            if any(h in low for h in JTBD_HINTS):
                out.append((file, sent))
    return out


def render(question: str, transcripts: dict[str, str], themes, pains, jtbds) -> str:
    lines = [
        f"# Research Synthesis",
        "",
        f"## Research question",
        question or "_(not specified)_",
        "",
        f"## Methodology",
        f"- Interviews analyzed: **{len(transcripts)}**",
        f"- Files: {', '.join(os.path.basename(f) for f in transcripts) or '(none)'}",
        "",
        "## Themes (ranked)",
    ]
    for theme, count, ex in themes:
        ex_line = ex[0] if ex else ("", "")
        verbatim = ex_line[1] if ex_line else ""
        src = os.path.basename(ex_line[0]) if ex_line else ""
        lines.append(f"- **{theme}** — {count} mentions — _\"{verbatim}\"_ ({src})")

    lines += ["", "## Pain points (verbatim)"]
    for file, sent in pains[:15]:
        lines.append(f"- _\"{sent}\"_ — `{os.path.basename(file)}`")

    lines += ["", "## JTBD signals"]
    for file, sent in jtbds[:15]:
        lines.append(f"- _\"{sent}\"_ — `{os.path.basename(file)}`")

    lines += [
        "",
        "## Recommendations",
        "- Validate the top theme with a quantitative survey to size impact.",
        "- Map pain points to the user journey; prioritize top 3 by frequency × severity.",
        "- Convert JTBD statements into outcome-oriented opportunity bets.",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True, help="Folder containing transcripts")
    ap.add_argument("--question", default="")
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        print(f"Not a directory: {args.dir}", file=sys.stderr)
        return 2

    transcripts = read_transcripts(args.dir)
    if not transcripts:
        print("No transcripts found (.txt/.md/.vtt).", file=sys.stderr)
        return 1

    themes = extract_themes(transcripts)
    pains = find_pain_points(transcripts)
    jtbds = find_jtbd(transcripts)
    out = render(args.question, transcripts, themes, pains, jtbds)
    if args.out == "-":
        print(out)
    else:
        Path(args.out).write_text(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
