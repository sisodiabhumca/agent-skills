#!/usr/bin/env python3
"""support-sla-breach-detector

Reads a vendor-neutral support ticket timeline CSV export and flags SLA breaches.

Input CSV required columns:
- ticket_id
- priority
- created_at (ISO 8601)
- first_response_at (ISO 8601 or empty)
- resolved_at (ISO 8601 or empty)

SLA input format:
- "P1=30,P2=120" (minutes)

Outputs human-readable summary and optional JSON report.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple


def _parse_iso(ts: str) -> Optional[datetime]:
    ts = (ts or "").strip()
    if not ts:
        return None
    # Support trailing Z
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def _parse_sla_map(s: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid SLA mapping '{part}' (expected KEY=MINUTES)")
        k, v = part.split("=", 1)
        out[k.strip()] = int(v.strip())
    return out


def _minutes_between(a: Optional[datetime], b: Optional[datetime]) -> Optional[float]:
    if a is None or b is None:
        return None
    return (b - a).total_seconds() / 60.0


@dataclass
class TicketResult:
    ticket_id: str
    priority: str
    minutes_to_first_response: Optional[float]
    minutes_to_resolution: Optional[float]
    response_sla_minutes: Optional[int]
    resolution_sla_minutes: Optional[int]
    breach: str  # none|response|resolution|both|unknown_priority

    def to_dict(self) -> Dict:
        return {
            "ticket_id": self.ticket_id,
            "priority": self.priority,
            "minutes_to_first_response": self.minutes_to_first_response,
            "minutes_to_resolution": self.minutes_to_resolution,
            "response_sla_minutes": self.response_sla_minutes,
            "resolution_sla_minutes": self.resolution_sla_minutes,
            "breach": self.breach,
        }


def analyze(csv_path: str, response_sla: Dict[str, int], resolution_sla: Dict[str, int]) -> Dict:
    results: List[TicketResult] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"ticket_id", "priority", "created_at", "first_response_at", "resolved_at"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for row in reader:
            tid = (row.get("ticket_id") or "").strip()
            prio = (row.get("priority") or "").strip()
            created = _parse_iso(row.get("created_at") or "")
            first_resp = _parse_iso(row.get("first_response_at") or "")
            resolved = _parse_iso(row.get("resolved_at") or "")

            m_resp = _minutes_between(created, first_resp)
            m_res = _minutes_between(created, resolved)

            resp_sla = response_sla.get(prio)
            res_sla = resolution_sla.get(prio)

            breach = "none"
            if resp_sla is None or res_sla is None:
                breach = "unknown_priority"
            else:
                resp_breach = (m_resp is not None) and (m_resp > resp_sla)
                res_breach = (m_res is not None) and (m_res > res_sla)
                if resp_breach and res_breach:
                    breach = "both"
                elif resp_breach:
                    breach = "response"
                elif res_breach:
                    breach = "resolution"

            results.append(
                TicketResult(
                    ticket_id=tid,
                    priority=prio,
                    minutes_to_first_response=m_resp,
                    minutes_to_resolution=m_res,
                    response_sla_minutes=resp_sla,
                    resolution_sla_minutes=res_sla,
                    breach=breach,
                )
            )

    breached = [r for r in results if r.breach in {"response", "resolution", "both"}]

    by_priority: Dict[str, Dict[str, int]] = {}
    for r in results:
        by_priority.setdefault(r.priority, {"total": 0, "breached": 0})
        by_priority[r.priority]["total"] += 1
        if r in breached:
            by_priority[r.priority]["breached"] += 1

    return {
        "summary": {
            "total_tickets": len(results),
            "breached_tickets": len(breached),
            "by_priority": by_priority,
        },
        "tickets": [r.to_dict() for r in results],
        "breaches": [r.to_dict() for r in breached],
    }


def _print_summary(report: Dict) -> None:
    s = report["summary"]
    print(f"Total tickets: {s['total_tickets']}")
    print(f"Breached tickets: {s['breached_tickets']}")
    print("Breaches by priority:")
    for prio in sorted(s["by_priority"].keys()):
        d = s["by_priority"][prio]
        print(f"  - {prio}: {d['breached']}/{d['total']}")

    if report["breaches"]:
        print("\nBreached ticket IDs:")
        for r in report["breaches"]:
            print(f"  - {r['ticket_id']} ({r['breach']})")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Detect SLA breaches from a support ticket export CSV.")
    ap.add_argument("--input", required=True, help="Path to ticket export CSV")
    ap.add_argument("--response-sla", required=True, help="Priority→minutes mapping, e.g. P1=30,P2=120")
    ap.add_argument("--resolution-sla", required=True, help="Priority→minutes mapping, e.g. P1=240,P2=1440")
    ap.add_argument("--json-out", default=None, help="Optional path to write JSON report")
    args = ap.parse_args(argv)

    response_sla = _parse_sla_map(args.response_sla)
    resolution_sla = _parse_sla_map(args.resolution_sla)

    report = analyze(args.input, response_sla, resolution_sla)
    _print_summary(report)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
