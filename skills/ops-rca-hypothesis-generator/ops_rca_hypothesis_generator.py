#!/usr/bin/env python3
"""ops-rca-hypothesis-generator

Given incident symptoms and a list of recent changes, generates a prioritized set
of testable RCA hypotheses and investigation steps.

Vendor-neutral: produces generic checks (logs/metrics/config/rollbacks) without
assuming any specific monitoring or deployment tool.
"""

import argparse
import json
import math
import re
from datetime import datetime, timezone


WORD_RE = re.compile(r"[a-z0-9]{3,}")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_ts(s: str):
    # Accept ISO8601 with Z or offset.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def keywords(text: str):
    return set(WORD_RE.findall((text or "").lower()))


def time_proximity_score(change_ts, start_ts, end_ts):
    # 1.0 if within window, else decays with distance
    if start_ts <= change_ts <= end_ts:
        return 1.0
    # distance in minutes to nearest boundary
    dist = min(abs((change_ts - start_ts).total_seconds()), abs((change_ts - end_ts).total_seconds())) / 60.0
    return 1.0 / (1.0 + dist / 30.0)  # half-life-ish 30 min


def overlap_score(a: set, b: set):
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


def build_hypotheses(incident, changes):
    start_ts = parse_ts(incident["window"]["start"])
    end_ts = parse_ts(incident["window"]["end"])

    symptom_blob = " ".join(incident.get("symptoms", [])) + " " + " ".join(incident.get("affected_components", []))
    incident_kw = keywords(symptom_blob)

    scored = []
    for ch in changes:
        cts = parse_ts(ch["timestamp"])
        tscore = time_proximity_score(cts, start_ts, end_ts)
        cblob = " ".join([ch.get("service", ""), ch.get("type", ""), ch.get("description", "")])
        ckw = keywords(cblob)
        kscore = overlap_score(incident_kw, ckw)
        score = 0.7 * tscore + 0.3 * kscore
        scored.append((score, ch, tscore, kscore))

    scored.sort(key=lambda x: x[0], reverse=True)

    hypotheses = []
    for i, (score, ch, tscore, kscore) in enumerate(scored[:10], start=1):
        service = ch.get("service") or "(unknown service)"
        desc = ch.get("description") or ch.get("id") or "(change)"
        symptom = incident.get("symptoms", ["service degradation"])[0]
        hyp = f"Recent change '{desc}' in {service} may have contributed to '{symptom}' via a configuration/performance/regression mechanism."

        next_steps = [
            "Check error-rate and latency metrics around the incident window for the affected services.",
            "Review application logs for new stack traces, timeouts, or dependency failures starting near the change time.",
            "Compare configuration and environment variables before/after the change.",
            "If safe, perform a canary rollback or disable the new behavior to see if symptoms abate.",
            "Validate dependencies (database, cache, third-party APIs) for saturation, throttling, or connectivity issues.",
        ]

        evidence = {
            "change_id": ch.get("id"),
            "change_timestamp_utc": parse_ts(ch["timestamp"]).isoformat().replace("+00:00", "Z"),
            "time_proximity_score": round(tscore, 4),
            "keyword_overlap_score": round(kscore, 4),
        }

        hypotheses.append(
            {
                "rank": i,
                "score": round(score, 4),
                "hypothesis": hyp,
                "evidence": evidence,
                "next_steps": next_steps,
            }
        )

    return {
        "incident_summary": {
            "title": incident.get("title"),
            "window": incident.get("window"),
            "impact": incident.get("impact"),
            "affected_components": incident.get("affected_components", []),
        },
        "hypotheses": hypotheses,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--incident", required=True)
    ap.add_argument("--changes", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    incident = load_json(args.incident)
    changes = load_json(args.changes)

    out = build_hypotheses(incident, changes)
    print(f"Generated {len(out['hypotheses'])} hypotheses")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
