#!/usr/bin/env python3
"""Vendor-neutral incident timeline normalizer.

Normalizes event logs with mixed timestamp formats, sorts them, and computes
basic incident phase durations.

Stdlib-only.
"""

import argparse
import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple


def parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    # epoch seconds
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    s = str(value).strip()
    if not s:
        return None

    # epoch seconds in string
    if s.isdigit():
        return datetime.fromtimestamp(float(s), tz=timezone.utc)

    # ISO 8601
    try:
        # handle trailing Z
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass

    # RFC 2822-ish
    try:
        dt = parsedate_to_datetime(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass

    return None


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def first_event_ts(events: List[Dict[str, Any]], event_type: str) -> Optional[datetime]:
    for e in events:
        if str(e.get("type", "")).lower() == event_type:
            return e.get("_ts")
    return None


def diff_s(a: Optional[datetime], b: Optional[datetime]) -> Optional[int]:
    if not a or not b:
        return None
    return int((b - a).total_seconds())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events_json", required=True)
    ap.add_argument("--out_json", required=True)
    args = ap.parse_args()

    with open(args.events_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    incident_id = str(data.get("incident_id", ""))
    raw_events = data.get("events") or []

    parsed: List[Dict[str, Any]] = []
    skipped = 0
    for e in raw_events:
        ts = parse_ts(e.get("timestamp"))
        if not ts:
            skipped += 1
            continue
        parsed.append({"_ts": ts, "type": e.get("type"), "message": e.get("message", "")})

    parsed.sort(key=lambda x: x["_ts"])

    t0 = parsed[0]["_ts"] if parsed else None
    detected = first_event_ts(parsed, "detected")
    mitigated = first_event_ts(parsed, "mitigated")
    resolved = first_event_ts(parsed, "resolved")

    out = {
        "incident_id": incident_id,
        "skipped_events": skipped,
        "timeline": [
            {"ts_iso": iso(e["_ts"]), "type": e.get("type"), "message": e.get("message", "")}
            for e in parsed
        ],
        "metrics": {
            "time_to_detect_s": diff_s(t0, detected),
            "time_to_mitigate_s": diff_s(detected, mitigated),
            "time_to_resolve_s": diff_s(detected, resolved),
        },
    }

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(json.dumps({"out_json": args.out_json, "events": len(parsed), "skipped": skipped}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
