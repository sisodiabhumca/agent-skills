#!/usr/bin/env python3
import argparse
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def parse_ts(s: str) -> Optional[datetime]:
    s = s.strip()
    # Accept Z or offset; if none, assume UTC
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out")
    ap.add_argument("--gap-minutes", type=int, default=20)
    args = ap.parse_args()

    events: List[Dict[str, Any]] = []
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            # split first token as timestamp
            parts = line.split(maxsplit=1)
            if not parts:
                continue
            ts = parse_ts(parts[0])
            if not ts:
                continue
            msg = parts[1] if len(parts) > 1 else ""
            events.append({"ts": ts, "message": msg})

    events.sort(key=lambda e: e["ts"])

    # build clusters and gaps
    clusters: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []
    if events:
        cur_start = events[0]["ts"]
        cur_end = events[0]["ts"]
        cur_count = 1
        for prev, nxt in zip(events, events[1:]):
            delta_min = (nxt["ts"] - prev["ts"]).total_seconds() / 60.0
            if delta_min > args.gap_minutes:
                gaps.append({
                    "from_ts": prev["ts"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "to_ts": nxt["ts"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "minutes": round(delta_min, 2),
                })

            if delta_min <= args.gap_minutes:
                cur_end = nxt["ts"]
                cur_count += 1
            else:
                clusters.append({
                    "start_ts": cur_start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "end_ts": cur_end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "count": cur_count,
                })
                cur_start = nxt["ts"]
                cur_end = nxt["ts"]
                cur_count = 1
        clusters.append({
            "start_ts": cur_start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "end_ts": cur_end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "count": cur_count,
        })

    out_events = [{
        "ts": e["ts"].astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "message": e["message"],
    } for e in events]

    report = {
        "events": out_events,
        "clusters": clusters,
        "gaps": gaps,
        "stats": {
            "events_total": len(out_events),
            "clusters_total": len(clusters),
            "gaps_total": len(gaps),
        }
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
