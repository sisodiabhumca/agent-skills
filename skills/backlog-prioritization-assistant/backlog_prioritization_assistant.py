#!/usr/bin/env python3
"""Vendor-neutral backlog prioritization assistant.

Reads a backlog CSV and computes transparent prioritization scores.
Stdlib-only.
"""

import argparse
import csv
import json
from typing import Dict, List, Tuple


def fnum(v: str, default: float = 0.0) -> float:
    try:
        s = "" if v is None else str(v).strip()
        return default if s == "" else float(s)
    except Exception:
        return default


def score_item(item: Dict[str, str], method: str) -> Tuple[float, List[str]]:
    eps = 1e-9
    impact = fnum(item.get("impact"), 0.0)
    effort = fnum(item.get("effort"), 0.0)

    if method == "rice":
        reach = fnum(item.get("reach"), 0.0)
        conf = fnum(item.get("confidence"), 0.0)
        score = (reach * impact * conf) / max(effort, eps)
        return score, [f"RICE = reach({reach}) * impact({impact}) * confidence({conf}) / effort({effort})"]

    if method == "wsjf":
        cod = fnum(item.get("cost_of_delay"), 0.0)
        js = fnum(item.get("job_size"), 0.0)
        score = cod / max(js, eps)
        return score, [f"WSJF = cost_of_delay({cod}) / job_size({js})"]

    score = impact / max(effort, eps)
    return score, [f"Simple = impact({impact}) / effort({effort})"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--method", choices=["rice", "wsjf", "simple"], default="simple")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise SystemExit("No rows")

    required = {"id", "title", "impact", "effort"}
    missing = [c for c in required if c not in rows[0].keys()]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    scored = []
    for r in rows:
        score, expl = score_item(r, args.method)
        scored.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "method": args.method,
                "score": score,
                "impact": fnum(r.get("impact")),
                "effort": fnum(r.get("effort")),
                "explanations": expl,
            }
        )

    scored.sort(key=lambda x: (-x["score"], -x["impact"], x["effort"]))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"summary": {"method": args.method, "count": len(scored)}, "items": scored}, f, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
