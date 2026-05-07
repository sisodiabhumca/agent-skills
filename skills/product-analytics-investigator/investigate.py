"""Product Analytics Investigator.

Computes funnel conversion and segment deltas between two time windows.
Works against:
  - Amplitude Dashboard REST API (--source amplitude)
  - Mixpanel JQL/Insights API (--source mixpanel)
  - A CSV export with columns: timestamp,user_id,event,platform,plan,country (--source csv)

Outputs a Markdown memo to stdout (or --out path).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable


@dataclass
class Event:
    ts: datetime
    user_id: str
    event: str
    props: dict = field(default_factory=dict)


def _parse_ts(s: str) -> datetime:
    s = s.strip().replace("Z", "+00:00")
    return datetime.fromisoformat(s)


def load_csv(path: str) -> list[Event]:
    rows: list[Event] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(
                Event(
                    ts=_parse_ts(r["timestamp"]),
                    user_id=r["user_id"],
                    event=r["event"],
                    props={k: v for k, v in r.items() if k not in {"timestamp", "user_id", "event"}},
                )
            )
    return rows


def funnel_conversion(events: Iterable[Event], steps: list[str], window: tuple[datetime, datetime]) -> dict:
    start, end = window
    by_user: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        if start <= e.ts < end and e.event in steps:
            by_user[e.user_id].append(e)

    step_counts = [0] * len(steps)
    for uid, evs in by_user.items():
        evs.sort(key=lambda e: e.ts)
        idx = 0
        for ev in evs:
            if idx < len(steps) and ev.event == steps[idx]:
                step_counts[idx] += 1
                idx += 1
    return {
        "users_entered": step_counts[0] if step_counts else 0,
        "step_counts": step_counts,
        "conversion_pct": [(c / step_counts[0] * 100) if step_counts and step_counts[0] else 0.0 for c in step_counts],
    }


def segment_deltas(events: list[Event], steps: list[str], current: tuple, prior: tuple, segment_key: str) -> list[dict]:
    segments = sorted({e.props.get(segment_key, "(unknown)") for e in events})
    rows = []
    for seg in segments:
        seg_events = [e for e in events if e.props.get(segment_key) == seg]
        cur = funnel_conversion(seg_events, steps, current)
        prv = funnel_conversion(seg_events, steps, prior)
        if cur["users_entered"] < 100 and prv["users_entered"] < 100:
            note = "low-sample"
        else:
            note = ""
        cur_final = cur["conversion_pct"][-1] if cur["conversion_pct"] else 0
        prv_final = prv["conversion_pct"][-1] if prv["conversion_pct"] else 0
        rows.append(
            {
                "segment": seg,
                "users_current": cur["users_entered"],
                "users_prior": prv["users_entered"],
                "conv_current_pct": round(cur_final, 2),
                "conv_prior_pct": round(prv_final, 2),
                "delta_pp": round(cur_final - prv_final, 2),
                "note": note,
            }
        )
    rows.sort(key=lambda r: r["delta_pp"])
    return rows


def fetch_amplitude(api_key: str, secret: str, project_id: str, start: datetime, end: datetime) -> list[Event]:
    """Pull raw events from Amplitude Export API. Requires `requests` and `gzip`."""
    import gzip
    import io
    import zipfile

    import requests  # type: ignore

    url = "https://amplitude.com/api/2/export"
    params = {"start": start.strftime("%Y%m%dT%H"), "end": end.strftime("%Y%m%dT%H")}
    r = requests.get(url, params=params, auth=(api_key, secret), timeout=120)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    events: list[Event] = []
    for name in z.namelist():
        with z.open(name) as f:
            for line in gzip.GzipFile(fileobj=f):
                obj = json.loads(line)
                events.append(
                    Event(
                        ts=_parse_ts(obj["event_time"]),
                        user_id=str(obj.get("user_id") or obj.get("device_id")),
                        event=obj["event_type"],
                        props=obj.get("event_properties", {}) | obj.get("user_properties", {}),
                    )
                )
    return events


def fetch_mixpanel(api_secret: str, project_id: str, start: datetime, end: datetime) -> list[Event]:
    import requests  # type: ignore

    url = "https://data.mixpanel.com/api/2.0/export"
    params = {"from_date": start.date().isoformat(), "to_date": end.date().isoformat(), "project_id": project_id}
    r = requests.get(url, params=params, auth=(api_secret, ""), timeout=300)
    r.raise_for_status()
    events: list[Event] = []
    for line in r.iter_lines():
        if not line:
            continue
        obj = json.loads(line)
        p = obj.get("properties", {})
        events.append(
            Event(
                ts=datetime.fromtimestamp(p["time"], tz=timezone.utc),
                user_id=str(p.get("distinct_id", "")),
                event=obj["event"],
                props=p,
            )
        )
    return events


def render_memo(args, current_funnel, prior_funnel, seg_rows) -> str:
    cur_final = current_funnel["conversion_pct"][-1] if current_funnel["conversion_pct"] else 0
    prv_final = prior_funnel["conversion_pct"][-1] if prior_funnel["conversion_pct"] else 0
    delta = cur_final - prv_final
    direction = "dropped" if delta < 0 else "improved"

    lines = [
        f"# Funnel Investigation — {' → '.join(args.steps)}",
        "",
        "## TL;DR",
        f"End-to-end conversion {direction} by **{abs(delta):.2f} pp** "
        f"({prv_final:.2f}% → {cur_final:.2f}%) "
        f"between the prior window and the current window.",
        "",
        "## Funnel — current window",
        "| Step | Users | Conversion from step 1 |",
        "|---|---|---|",
    ]
    for step, count, pct in zip(args.steps, current_funnel["step_counts"], current_funnel["conversion_pct"]):
        lines.append(f"| {step} | {count} | {pct:.2f}% |")

    lines += [
        "",
        f"## Segment deltas by `{args.segment}` (sorted, biggest drops first)",
        "| Segment | Users (cur) | Users (prior) | Conv cur | Conv prior | Δ pp | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in seg_rows[:25]:
        lines.append(
            f"| {row['segment']} | {row['users_current']} | {row['users_prior']} | "
            f"{row['conv_current_pct']}% | {row['conv_prior_pct']}% | {row['delta_pp']} | {row['note']} |"
        )

    lines += [
        "",
        "## Hypotheses (to validate)",
        "1. Release/experiment effect — overlay deploy timeline on the worst-affected segments.",
        "2. Tracking regression — verify event volume vs. server logs for the dropped step.",
        "3. External factor — check marketing mix, seasonality, or platform outages.",
        "",
        "## Recommended next steps",
        "- [ ] Owner: data PM — confirm tracking integrity for impacted step",
        "- [ ] Owner: eng lead — bisect releases in the window",
        "- [ ] Owner: PM — review segment-specific UX for top-impacted segment",
    ]
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", choices=["csv", "amplitude", "mixpanel"], required=True)
    p.add_argument("--csv", help="Path to events CSV (when --source=csv)")
    p.add_argument("--steps", nargs="+", required=True, help="Funnel steps in order")
    p.add_argument("--segment", default="platform", help="Property to slice by (platform/plan/country)")
    p.add_argument("--current-days", type=int, default=14)
    p.add_argument("--prior-days", type=int, default=14)
    p.add_argument("--end", default=None, help="ISO end timestamp (defaults to now UTC)")
    p.add_argument("--out", default="-", help="Output path or - for stdout")
    args = p.parse_args()

    end = _parse_ts(args.end) if args.end else datetime.now(timezone.utc)
    cur_start = end - timedelta(days=args.current_days)
    prv_end = cur_start
    prv_start = prv_end - timedelta(days=args.prior_days)

    if args.source == "csv":
        if not args.csv:
            print("--csv required when --source=csv", file=sys.stderr)
            return 2
        events = load_csv(args.csv)
    elif args.source == "amplitude":
        events = fetch_amplitude(
            os.environ["AMPLITUDE_API_KEY"],
            os.environ["AMPLITUDE_SECRET_KEY"],
            os.environ.get("AMPLITUDE_PROJECT_ID", ""),
            prv_start,
            end,
        )
    else:
        events = fetch_mixpanel(
            os.environ["MIXPANEL_API_SECRET"],
            os.environ.get("MIXPANEL_PROJECT_ID", ""),
            prv_start,
            end,
        )

    cur = funnel_conversion(events, args.steps, (cur_start, end))
    prv = funnel_conversion(events, args.steps, (prv_start, prv_end))
    seg = segment_deltas(events, args.steps, (cur_start, end), (prv_start, prv_end), args.segment)
    memo = render_memo(args, cur, prv, seg)

    if args.out == "-":
        print(memo)
    else:
        with open(args.out, "w") as f:
            f.write(memo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
