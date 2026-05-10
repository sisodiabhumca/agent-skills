#!/usr/bin/env python3
import argparse
import csv
import json
from datetime import datetime
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple


def parse_date(s: str) -> datetime:
    return datetime.strptime(s.strip(), "%Y-%m-%d")


def rolling_stats(values: List[float], window: int, idx: int) -> Optional[Tuple[float, float]]:
    start = max(0, idx - window)
    hist = values[start:idx]
    if len(hist) < max(5, window // 2):
        return None
    m = mean(hist)
    sd = pstdev(hist)
    return m, sd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--window", type=int, default=14)
    ap.add_argument("--z", type=float, default=3.0)
    ap.add_argument("--out")
    args = ap.parse_args()

    rows: List[Tuple[datetime, float]] = []
    with open(args.input, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if not row:
                continue
            d = parse_date(row["date"])
            v = float(row["value"])
            rows.append((d, v))

    rows.sort(key=lambda x: x[0])
    dates = [d for d, _ in rows]
    values = [v for _, v in rows]

    anomalies: List[Dict[str, Any]] = []
    for i in range(len(values)):
        stats = rolling_stats(values, args.window, i)
        if not stats:
            continue
        m, sd = stats
        if sd == 0:
            continue
        z = (values[i] - m) / sd
        if abs(z) >= args.z:
            anomalies.append({
                "date": dates[i].strftime("%Y-%m-%d"),
                "value": values[i],
                "z": round(z, 3),
                "mean": round(m, 3),
                "std": round(sd, 3),
            })

    # recent summary
    last_n = min(7, len(values))
    recent_vals = values[-last_n:] if last_n else []
    direction = "flat"
    if last_n >= 2:
        if recent_vals[-1] > recent_vals[0]:
            direction = "up"
        elif recent_vals[-1] < recent_vals[0]:
            direction = "down"

    report = {
        "anomalies": anomalies,
        "recent_summary": {
            "last_date": dates[-1].strftime("%Y-%m-%d") if dates else None,
            "last_value": values[-1] if values else None,
            "last_7d_min": min(recent_vals) if recent_vals else None,
            "last_7d_max": max(recent_vals) if recent_vals else None,
            "direction": direction,
        },
        "params": {"window": args.window, "z": args.z},
        "stats": {"points": len(values), "anomalies": len(anomalies)},
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
