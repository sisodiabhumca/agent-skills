"""Incident Postmortem Builder.

Inputs:
  --timeline timeline.csv    columns: timestamp,event,actor,source
  --incident-id INC-1234
  --title "Checkout 5xx surge"
  --detected 2026-05-03T14:02:00Z
  --mitigated 2026-05-03T14:31:00Z
  --resolved 2026-05-03T15:10:00Z
  --impact-users 12000 --impact-revenue 4200

Emits a blameless postmortem to stdout (or --out).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt_dur(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"


def load_timeline(path: str) -> list[dict]:
    rows: list[dict] = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "ts": parse_ts(r["timestamp"]),
                    "event": r.get("event", "").strip(),
                    "actor": r.get("actor", "").strip(),
                    "source": r.get("source", "").strip(),
                }
            )
    rows.sort(key=lambda r: r["ts"])
    return rows


def render(args, timeline) -> str:
    started = parse_ts(args.started) if args.started else (timeline[0]["ts"] if timeline else None)
    detected = parse_ts(args.detected)
    mitigated = parse_ts(args.mitigated)
    resolved = parse_ts(args.resolved)

    ttd = (detected - started).total_seconds() if started else 0
    ttm = (mitigated - detected).total_seconds()
    ttr = (resolved - detected).total_seconds()

    lines = [
        f"# Postmortem — {args.incident_id}: {args.title}",
        "",
        f"- **Severity:** {args.severity}",
        f"- **Status:** Resolved",
        f"- **Started:** {started.isoformat() if started else 'unknown'}",
        f"- **Detected:** {detected.isoformat()}",
        f"- **Mitigated:** {mitigated.isoformat()}",
        f"- **Resolved:** {resolved.isoformat()}",
        "",
        "## Summary",
        f"{args.summary or '_(one-paragraph summary: what happened, who was impacted, how it was resolved)_'}",
        "",
        "## Impact",
        f"- Users affected: **{args.impact_users:,}**" if args.impact_users else "- Users affected: unknown",
        f"- Revenue impact: **${args.impact_revenue:,.0f}**" if args.impact_revenue else "- Revenue impact: unknown",
        f"- Customer-minutes lost (approx): **{int((ttr/60) * (args.impact_users or 0)):,}**" if args.impact_users else "",
        "",
        "## Detection & Response metrics",
        f"- **TTD (start → detected):** {fmt_dur(ttd)}",
        f"- **TTM (detected → mitigated):** {fmt_dur(ttm)}",
        f"- **TTR (detected → resolved):** {fmt_dur(ttr)}",
        "",
        "## Timeline (UTC)",
        "| Time | Event | Actor | Source |",
        "|---|---|---|---|",
    ]
    for row in timeline:
        lines.append(f"| {row['ts'].isoformat()} | {row['event']} | {row['actor'] or '—'} | {row['source'] or '—'} |")

    lines += [
        "",
        "## Root cause (blameless)",
        args.root_cause or "_Describe the system condition that allowed the failure. Avoid naming individuals._",
        "",
        "## Contributing factors",
        "- _Latent system condition_",
        "- _Detection gap_",
        "- _Process gap_",
        "",
        "## What went well",
        "- _e.g. on-call paged within SLA, rollback worked first try_",
        "",
        "## What went wrong",
        "- _e.g. alert was noisy and ignored for X minutes; runbook was outdated_",
        "",
        "## Action items",
        "| ID | Action | Type | Owner | Due |",
        "|---|---|---|---|---|",
        "| AI-1 | _Add SLO alert on 5xx_ | detect | sre-lead | YYYY-MM-DD |",
        "| AI-2 | _Add canary stage to deploy_ | prevent | platform-lead | YYYY-MM-DD |",
        "| AI-3 | _Update runbook for service X_ | mitigate | service-owner | YYYY-MM-DD |",
        "",
        "## Lessons",
        "- _Generalizable lessons for the org._",
    ]
    return "\n".join(l for l in lines if l != "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--incident-id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--severity", default="Sev2")
    ap.add_argument("--summary", default="")
    ap.add_argument("--root-cause", default="")
    ap.add_argument("--started", default="")
    ap.add_argument("--detected", required=True)
    ap.add_argument("--mitigated", required=True)
    ap.add_argument("--resolved", required=True)
    ap.add_argument("--timeline", required=True, help="CSV with timestamp,event,actor,source")
    ap.add_argument("--impact-users", type=int, default=0)
    ap.add_argument("--impact-revenue", type=float, default=0.0)
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    timeline = load_timeline(args.timeline)
    body = render(args, timeline)
    if args.out == "-":
        print(body)
    else:
        Path(args.out).write_text(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
