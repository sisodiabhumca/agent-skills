#!/usr/bin/env python3
"""Vendor-neutral customer journey gap analyzer.

Reads a simple funnel CSV and emits ranked gaps with templated experiments.
Stdlib-only.
"""

import argparse
import csv
import json
import math
import sys


SUGGESTIONS = [
    ("signup", ["Reduce form fields", "Add SSO", "Clarify privacy and trust cues"]),
    ("onboarding", ["Shorten onboarding steps", "Add progress indicator", "Provide sample data/templates"]),
    ("checkout", ["Add more payment options", "Show total cost earlier", "Improve error messaging"]),
    ("activation", ["Add guided checklist", "Improve empty states", "Send nudges within first day"]),
]


def parse_float(x):
    try:
        return float(x)
    except Exception:
        return None


def suggest_for_stage(stage_name):
    low = stage_name.lower()
    for key, ideas in SUGGESTIONS:
        if key in low:
            return ideas
    return [
        "Reduce friction in the step",
        "Improve clarity of instructions and errors",
        "Add trust signals and set expectations",
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    args = ap.parse_args()

    rows = []
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if not rows:
        raise SystemExit("input CSV has no rows")

    required = {"stage", "entered", "completed"}
    if not required.issubset(set(rows[0].keys())):
        raise SystemExit("CSV must include columns: stage, entered, completed")

    stages = []
    for r in rows:
        stage = (r.get("stage") or "").strip()
        entered = parse_float(r.get("entered"))
        completed = parse_float(r.get("completed"))
        if not stage:
            raise SystemExit("stage cannot be empty")
        if entered is None or completed is None:
            raise SystemExit(f"entered/completed must be numeric for stage {stage}")
        entered = max(0.0, entered)
        completed = max(0.0, completed)
        if completed > entered and entered > 0:
            completed = entered

        conv = (completed / entered) if entered > 0 else 0.0
        drop = max(0.0, entered - completed)
        drop_rate = (drop / entered) if entered > 0 else 0.0

        stages.append(
            {
                "stage": stage,
                "entered": entered,
                "completed": completed,
                "conversion_rate": round(conv, 4),
                "dropoff": drop,
                "dropoff_rate": round(drop_rate, 4),
                "avg_time_seconds": parse_float(r.get("avg_time_seconds")),
                "notes": r.get("notes"),
            }
        )

    # Impact score: volume-weighted drop-off with extra weight for low conversion
    for s in stages:
        s["impact_score"] = round(s["dropoff"] * (1.0 + (1.0 - s["conversion_rate"])), 4)

    ranked = sorted(stages, key=lambda x: x["impact_score"], reverse=True)
    top_gaps = []
    for s in ranked[:5]:
        top_gaps.append(
            {
                "stage": s["stage"],
                "impact_score": s["impact_score"],
                "dropoff": s["dropoff"],
                "dropoff_rate": s["dropoff_rate"],
                "suggested_experiments": suggest_for_stage(s["stage"]),
            }
        )

    overall_entered = stages[0]["entered"]
    overall_completed = stages[-1]["completed"]
    overall_conversion = (overall_completed / overall_entered) if overall_entered > 0 else 0.0

    out = {
        "summary": {
            "stages": len(stages),
            "overall_conversion": round(overall_conversion, 4),
            "overall_entered": overall_entered,
            "overall_completed": overall_completed,
        },
        "stages": stages,
        "top_gaps": top_gaps,
    }

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
