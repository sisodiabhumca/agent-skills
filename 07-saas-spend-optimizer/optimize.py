"""SaaS Spend Optimizer.

Inputs:
  --subs sample/subscriptions.csv
    columns: vendor,category,plan,seats,cost_monthly,renewal_date,critical
  --usage sample/usage.csv (optional)
    columns: vendor,user,last_active   (last_active ISO date)

Emits a Markdown report with top savings opportunities, renewal calendar, and duplicates.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def read_csv(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def parse_date(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def analyze(subs: list[dict], usage: list[dict], inactive_days: int = 30) -> dict:
    today = datetime.now(timezone.utc)
    inactive_cutoff = today - timedelta(days=inactive_days)

    usage_by_vendor: dict[str, set[str]] = defaultdict(set)
    active_by_vendor: dict[str, set[str]] = defaultdict(set)
    for u in usage:
        v = u["vendor"]
        usage_by_vendor[v].add(u["user"])
        la = parse_date(u.get("last_active", ""))
        if la and la >= inactive_cutoff:
            active_by_vendor[v].add(u["user"])

    opportunities: list[dict] = []
    renewals: list[dict] = []
    by_category: dict[str, list[dict]] = defaultdict(list)

    for s in subs:
        seats = int(s.get("seats") or 0)
        monthly = float(s.get("cost_monthly") or 0)
        per_seat = monthly / seats if seats else 0
        annual = monthly * 12
        critical = (s.get("critical") or "").strip().lower() in {"true", "yes", "1"}
        rdate = parse_date(s.get("renewal_date"))
        v = s["vendor"]
        cat = s.get("category", "uncategorized") or "uncategorized"

        active = len(active_by_vendor.get(v, set()))
        provisioned_users = max(len(usage_by_vendor.get(v, set())), seats)
        unused_seats = max(seats - active, 0) if active or v in active_by_vendor else 0

        # Unused-seat opportunity
        if seats and active and unused_seats > 0 and per_seat > 0:
            est_savings = unused_seats * per_seat * 12
            opportunities.append({
                "type": "unused_seats",
                "vendor": v,
                "annual_savings_usd": round(est_savings, 2),
                "detail": f"{unused_seats} of {seats} seats inactive >{inactive_days}d",
                "action": f"Reclaim {unused_seats} seats at next renewal",
                "critical": critical,
                "confidence": "high",
            })

        # Dead tool: no active users at all (and we have usage data for it)
        if v in usage_by_vendor and active == 0 and not critical:
            opportunities.append({
                "type": "dead_tool",
                "vendor": v,
                "annual_savings_usd": round(annual, 2),
                "detail": f"No active users in {inactive_days}d",
                "action": f"Cancel {v} at renewal {s.get('renewal_date','')}",
                "critical": critical,
                "confidence": "high",
            })
        elif v not in usage_by_vendor:
            opportunities.append({
                "type": "no_usage_data",
                "vendor": v,
                "annual_savings_usd": 0,
                "detail": "No usage data — instrument before recommending action",
                "action": "Connect SSO/usage feed",
                "critical": critical,
                "confidence": "low",
            })

        if rdate and rdate <= today + timedelta(days=90):
            days = (rdate - today).days
            renewals.append({"vendor": v, "renewal_date": rdate.date().isoformat(), "days": days, "annual": annual})

        by_category[cat].append({"vendor": v, "annual": annual})

    duplicates = []
    for cat, items in by_category.items():
        if len(items) > 1:
            duplicates.append({
                "category": cat,
                "vendors": [i["vendor"] for i in items],
                "combined_annual_usd": round(sum(i["annual"] for i in items), 2),
            })

    opportunities.sort(key=lambda o: o["annual_savings_usd"], reverse=True)
    renewals.sort(key=lambda r: r["days"])

    return {"opportunities": opportunities, "renewals": renewals, "duplicates": duplicates}


def render(report: dict) -> str:
    lines = ["# SaaS Spend Optimization Report", ""]
    total = sum(o["annual_savings_usd"] for o in report["opportunities"])
    lines.append(f"**Estimated annualized savings identified:** ${total:,.0f}")
    lines.append("")
    lines.append("## Top opportunities")
    lines.append("| Type | Vendor | Annual savings | Detail | Action | Confidence |")
    lines.append("|---|---|---|---|---|---|")
    for o in report["opportunities"][:25]:
        crit = " 🛡️ critical" if o["critical"] else ""
        lines.append(f"| {o['type']} | {o['vendor']}{crit} | ${o['annual_savings_usd']:,.0f} | {o['detail']} | {o['action']} | {o['confidence']} |")

    lines += ["", "## Renewal calendar (next 90 days)", "| Date | Vendor | Annual | Days |", "|---|---|---|---|"]
    for r in report["renewals"]:
        lines.append(f"| {r['renewal_date']} | {r['vendor']} | ${r['annual']:,.0f} | {r['days']} |")

    lines += ["", "## Duplicate tooling by category"]
    for d in report["duplicates"]:
        lines.append(f"- **{d['category']}**: {', '.join(d['vendors'])} — combined ${d['combined_annual_usd']:,.0f}/yr — consolidate to one vendor at next renewal.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subs", required=True)
    ap.add_argument("--usage", default=None)
    ap.add_argument("--inactive-days", type=int, default=30)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    subs = read_csv(args.subs)
    usage = read_csv(args.usage) if args.usage else []
    rep = analyze(subs, usage, args.inactive_days)
    md = render(rep)
    if args.out == "-":
        print(md)
    else:
        Path(args.out).write_text(md)
    if args.json:
        print(json.dumps(rep, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
