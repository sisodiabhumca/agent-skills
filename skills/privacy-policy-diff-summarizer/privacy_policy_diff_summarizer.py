#!/usr/bin/env python3
"""Vendor-neutral privacy policy diff summarizer.

Heuristic, paragraph-level diff with simple risk flags.
Stdlib-only.
"""

import argparse
import difflib
import json
import re
import sys


def normalize(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def split_paragraphs(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    # de-noise very short paragraphs (headings) by keeping them as-is
    return paras


RISK_RULES = [
    {
        "flag": "adds_location_data",
        "keywords": ["precise location", "geolocation", "location data"],
        "severity": "high",
    },
    {
        "flag": "adds_biometric_or_health_data",
        "keywords": ["biometric", "fingerprint", "face scan", "health data"],
        "severity": "high",
    },
    {
        "flag": "adds_children_data",
        "keywords": ["children", "under 13", "under the age of"],
        "severity": "high",
    },
    {
        "flag": "adds_advertising_sharing",
        "keywords": ["advertising", "ad partners", "targeted ads", "behavioral advertising"],
        "severity": "high",
    },
    {
        "flag": "adds_affiliates_or_partners_sharing",
        "keywords": ["affiliates", "partners", "third parties"],
        "severity": "medium",
    },
    {
        "flag": "extends_retention",
        "keywords": ["retain", "retention", "as long as necessary", "indefinitely"],
        "severity": "medium",
    },
    {
        "flag": "adds_cross_border_transfers",
        "keywords": ["cross-border", "international", "outside your country", "transfer"],
        "severity": "medium",
    },
]


def risk_flags(added, changed_pairs):
    hits = []

    def scan(text, where):
        low = text.lower()
        for rule in RISK_RULES:
            for kw in rule["keywords"]:
                if kw in low:
                    hits.append(
                        {
                            "flag": rule["flag"],
                            "severity": rule["severity"],
                            "keyword": kw,
                            "where": where,
                            "evidence": text[:280],
                        }
                    )
                    break

    for p in added:
        scan(p, "added_paragraph")
    for pair in changed_pairs:
        scan(pair["new"], "changed_paragraph")

    # dedupe by flag+where+keyword
    seen = set()
    out = []
    for h in hits:
        key = (h["flag"], h["where"], h["keyword"])
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def match_changed_pairs(removed, added, top_k=5):
    pairs = []
    for a in added:
        best = None
        best_ratio = 0.0
        for r in removed:
            ratio = difflib.SequenceMatcher(None, r, a).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best = r
        if best is not None and best_ratio >= 0.55:
            pairs.append({"old": best, "new": a, "similarity": round(best_ratio, 3)})

    pairs.sort(key=lambda x: x["similarity"], reverse=True)
    return pairs[:top_k]


def material_score(added, removed, flags):
    # Heuristic: base on amount of text + severity-weighted flags
    added_len = sum(len(x) for x in added)
    removed_len = sum(len(x) for x in removed)
    text_score = min(60, int((added_len + removed_len) / 1200 * 60))

    sev = {"high": 20, "medium": 10, "low": 5}
    flag_score = sum(sev.get(f["severity"], 5) for f in flags)

    return max(0, min(100, text_score + flag_score))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--max", type=int, default=10, help="max paragraphs to include")
    args = ap.parse_args()

    old_txt = normalize(open(args.old, "r", encoding="utf-8").read())
    new_txt = normalize(open(args.new, "r", encoding="utf-8").read())

    old_paras = split_paragraphs(old_txt)
    new_paras = split_paragraphs(new_txt)

    sm = difflib.SequenceMatcher(None, old_paras, new_paras)
    added = []
    removed = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("delete", "replace"):
            removed.extend(old_paras[i1:i2])
        if tag in ("insert", "replace"):
            added.extend(new_paras[j1:j2])

    changed_pairs = match_changed_pairs(removed, added, top_k=args.max)
    flags = risk_flags(added, changed_pairs)
    score = material_score(added, removed, flags)

    out = {
        "material_change_score": score,
        "counts": {
            "old_paragraphs": len(old_paras),
            "new_paragraphs": len(new_paras),
            "added_paragraphs": len(added),
            "removed_paragraphs": len(removed),
            "risk_flags": len(flags),
        },
        "added_paragraphs": added[: args.max],
        "removed_paragraphs": removed[: args.max],
        "changed_paragraph_pairs": changed_pairs,
        "risk_flags": flags,
        "disclaimer": "Heuristic summary only; not legal advice.",
    }

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
