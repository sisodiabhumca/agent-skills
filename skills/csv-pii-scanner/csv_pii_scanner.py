#!/usr/bin/env python3
import argparse
import csv
import json
import re
from typing import Dict, List, Any, Tuple

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
SSN_RE = re.compile(r"^\d{3}-\d{2}-\d{4}$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9\-\s\(\)]{6,}$")
CC_RE = re.compile(r"^(?:\d[ -]*?){13,19}$")

HEADER_KEYWORDS = {
    "high": ["ssn", "social", "passport", "credit", "card", "cc", "iban"],
    "medium": ["email", "phone", "mobile", "address", "dob", "birth", "ip"],
    "low": ["name", "first", "last", "full", "zip", "postal", "city", "state"],
}


def redact(v: str) -> str:
    v = v.strip()
    if not v:
        return v
    if len(v) <= 4:
        return "*" * len(v)
    return v[:2] + "*" * (len(v) - 4) + v[-2:]


def luhn_ok(num: str) -> bool:
    digits = [int(c) for c in re.sub(r"\D", "", num)]
    if len(digits) < 13 or len(digits) > 19:
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


def score_column(header: str, values: List[str]) -> Tuple[str, List[str], List[str]]:
    h = header.lower()
    reasons: List[str] = []

    header_risk = None
    for risk, kws in HEADER_KEYWORDS.items():
        if any(kw in h for kw in kws):
            header_risk = risk
            reasons.append(f"header_keyword:{risk}")
            break

    hits = {"email": 0, "phone": 0, "ssn": 0, "ip": 0, "cc": 0}
    examples: List[str] = []

    for v in values:
        v = (v or "").strip()
        if not v:
            continue
        if EMAIL_RE.match(v):
            hits["email"] += 1
            examples.append(redact(v))
        elif SSN_RE.match(v):
            hits["ssn"] += 1
            examples.append(redact(v))
        elif IPV4_RE.match(v):
            hits["ip"] += 1
            examples.append(redact(v))
        elif PHONE_RE.match(v) and sum(c.isdigit() for c in v) >= 10:
            hits["phone"] += 1
            examples.append(redact(v))
        elif CC_RE.match(v) and luhn_ok(v):
            hits["cc"] += 1
            examples.append(redact(v))

    total = max(1, len([v for v in values if (v or "").strip()]))
    density = {k: v / total for k, v in hits.items()}

    value_risk = "none"
    if density["ssn"] > 0.02 or density["cc"] > 0.02:
        value_risk = "high"
        reasons.append("value_pattern:high")
    elif density["email"] > 0.05 or density["phone"] > 0.05 or density["ip"] > 0.10:
        value_risk = "medium"
        reasons.append("value_pattern:medium")
    elif any(density[k] > 0.10 for k in ["email", "phone", "ip"]):
        value_risk = "medium"
        reasons.append("value_pattern:medium")
    elif any(v > 0 for v in hits.values()):
        value_risk = "low"
        reasons.append("value_pattern:low")

    order = {"none": 0, "low": 1, "medium": 2, "high": 3}
    final = "none"
    # combine header and value
    candidates = [r for r in [header_risk, value_risk] if r]
    if candidates:
        final = max(candidates, key=lambda r: order.get(r, 0))

    # cap examples
    examples = examples[:5]

    if final != "none":
        if "email" in h:
            reasons.append("suggest:mask_or_hash_emails")
        if "phone" in h:
            reasons.append("suggest:mask_phone")
        if "ssn" in h or hits["ssn"] > 0:
            reasons.append("suggest:remove_or_tokenize_ssn")
        if hits["cc"] > 0:
            reasons.append("suggest:remove_payment_data")

    return final, reasons, examples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out")
    ap.add_argument("--max-rows", type=int, default=2000)
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        cols: Dict[str, List[str]] = {h: [] for h in headers}
        for i, row in enumerate(reader):
            if i >= args.max_rows:
                break
            for h in headers:
                cols[h].append(row.get(h, ""))

    suspected = []
    summary = {"high": 0, "medium": 0, "low": 0, "none": 0}
    for h in headers:
        risk, reasons, examples = score_column(h, cols.get(h, []))
        summary[risk] = summary.get(risk, 0) + 1
        if risk != "none":
            suspected.append({
                "column": h,
                "risk": risk,
                "reasons": sorted(set(reasons)),
                "examples_redacted": examples,
            })

    report: Dict[str, Any] = {
        "summary": summary,
        "suspected_columns": sorted(suspected, key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x["risk"], 0), reverse=True),
        "sampled_rows": min(args.max_rows, max((len(next(iter(cols.values()))) if cols else 0), 0)),
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
