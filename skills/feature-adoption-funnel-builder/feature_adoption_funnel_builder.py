#!/usr/bin/env python3
"""feature-adoption-funnel-builder

Builds a simple adoption funnel from event logs.

Input CSV columns:
- user_id
- event_name
- timestamp (ISO8601)

Vendor-neutral: works with generic exported event data.
"""

import argparse
import csv
import json
from datetime import datetime, timezone, timedelta
from statistics import median


def parse_ts(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def load_events(path):
    events = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            events.append(
                {
                    "user_id": row.get("user_id", "").strip(),
                    "event_name": row.get("event_name", "").strip(),
                    "timestamp": parse_ts(row.get("timestamp", "")),
                }
            )
    events.sort(key=lambda e: (e["user_id"], e["timestamp"]))
    return events


def build_funnel(events, steps, window_days=30):
    window = timedelta(days=window_days)

    # user -> list of events
    users = {}
    for e in events:
        users.setdefault(e["user_id"], []).append(e)

    reached_counts = [0 for _ in steps]
    step_deltas = [[] for _ in range(len(steps) - 1)]

    for uid, evs in users.items():
        t_prev = None
        t_first = None
        reached = 0

        for i, step in enumerate(steps):
            t_step = None
            for e in evs:
                if e["event_name"] != step:
                    continue
                if t_prev and e["timestamp"] < t_prev:
                    continue
                if t_first and e["timestamp"] - t_first > window:
                    continue
                t_step = e["timestamp"]
                break

            if t_step is None:
                break

            if i == 0:
                t_first = t_step
            else:
                step_deltas[i - 1].append((t_step - t_prev).total_seconds())

            t_prev = t_step
            reached = i + 1

        for i in range(reached):
            reached_counts[i] += 1

    conversions = []
    for i in range(len(steps) - 1):
        denom = reached_counts[i]
        num = reached_counts[i + 1]
        conversions.append(None if denom == 0 else round(num / denom, 4))

    med_deltas = []
    for d in step_deltas:
        med_deltas.append(None if not d else round(median(d), 2))

    return {
        "steps": steps,
        "counts": reached_counts,
        "conversions": conversions,
        "median_step_time_seconds": med_deltas,
        "window_days": window_days,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", required=True)
    ap.add_argument("--steps", required=True)
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--out")
    args = ap.parse_args()

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    if len(steps) < 2:
        raise SystemExit("--steps must include at least 2 comma-separated event names")

    events = load_events(args.events)
    rep = build_funnel(events, steps, args.window_days)

    print("Funnel counts:", rep["counts"])
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
