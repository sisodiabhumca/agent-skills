#!/usr/bin/env python3
"""Vendor-neutral CSV PII redactor.

Heuristically detects common PII patterns in CSV columns and redacts
columns whose match-rate exceeds a threshold.

Stdlib-only.
"""

import argparse
import csv
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)
IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
SSN_RE = re.compile(r"^\d{3}-?\d{2}-?\d{4}$")
# Very permissive; we score on match-rate threshold to avoid over-redaction.
PHONE_RE = re.compile(r"^(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}$")


def luhn_ok(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 12 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d2 = d * 2
            checksum += d2 - 9 if d2 > 9 else d2
        else:
            checksum += d
    return checksum % 10 == 0


def looks_like_cc(value: str) -> bool:
    v = re.sub(r"[\s-]", "", value.strip())
    if not v.isdigit():
        return False
    return luhn_ok(v)


@dataclass
class DetectorResult:
    type: str
    matches: int
    total_non_empty: int
    examples: List[str]

    @property
    def match_rate(self) -> float:
        if self.total_non_empty == 0:
            return 0.0
        return self.matches / self.total_non_empty


def truncate_example(s: str, max_len: int = 32) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def detect_value(detector_type: str, value: str) -> bool:
    v = value.strip()
    if not v:
        return False
    if detector_type == "email":
        return bool(EMAIL_RE.match(v))
    if detector_type == "phone":
        return bool(PHONE_RE.match(v))
    if detector_type == "ssn":
        return bool(SSN_RE.match(v))
    if detector_type == "ipv4":
        if not IPV4_RE.match(v):
            return False
        parts = v.split(".")
        return all(0 <= int(p) <= 255 for p in parts)
    if detector_type == "credit_card":
        return looks_like_cc(v)
    raise ValueError(f"Unknown detector: {detector_type}")


def analyze_column(values: List[str], detector_types: List[str], max_examples: int = 5) -> List[DetectorResult]:
    non_empty = [v for v in values if v.strip()]
    results: List[DetectorResult] = []
    for dt in detector_types:
        matches = 0
        examples: List[str] = []
        for v in non_empty:
            if detect_value(dt, v):
                matches += 1
                if len(examples) < max_examples:
                    examples.append(truncate_example(v))
        results.append(DetectorResult(type=dt, matches=matches, total_non_empty=len(non_empty), examples=examples))
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input_csv", required=True)
    ap.add_argument("--output_csv", required=True)
    ap.add_argument("--report_json", required=True)
    ap.add_argument("--redact_with", default="[REDACTED]")
    ap.add_argument("--min_match_rate", type=float, default=0.2)
    args = ap.parse_args()

    with open(args.input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    # Gather column values
    col_values: Dict[str, List[str]] = {fn: [] for fn in fieldnames}
    for r in rows:
        for fn in fieldnames:
            col_values[fn].append(r.get(fn, ""))

    detectors = ["email", "phone", "ssn", "ipv4", "credit_card"]

    report_cols = []
    redact_cols = set()
    for fn in fieldnames:
        results = analyze_column(col_values[fn], detectors)
        # redact if any detector exceeds threshold
        redacted = any(res.match_rate >= args.min_match_rate and res.matches > 0 for res in results)
        if redacted:
            redact_cols.add(fn)
        report_cols.append(
            {
                "name": fn,
                "redacted": redacted,
                "detectors": [
                    {
                        "type": res.type,
                        "matches": res.matches,
                        "total_non_empty": res.total_non_empty,
                        "match_rate": round(res.match_rate, 6),
                        "examples": res.examples,
                    }
                    for res in results
                ],
            }
        )

    # Write redacted CSV
    with open(args.output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            out = dict(r)
            for fn in redact_cols:
                if out.get(fn, "").strip():
                    out[fn] = args.redact_with
            writer.writerow(out)

    report = {
        "input_csv": args.input_csv,
        "output_csv": args.output_csv,
        "redact_with": args.redact_with,
        "min_match_rate": args.min_match_rate,
        "columns": report_cols,
    }

    with open(args.report_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(json.dumps({"redacted_columns": sorted(redact_cols), "report_json": args.report_json}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
