#!/usr/bin/env python3
"""Vendor-neutral pseudonymization field mapper.

Reads a dataset schema JSON and emits a recommended pseudonymization plan.

Design goals:
- No external dependencies (stdlib only)
- Conservative defaults (drop/redact high-risk fields)
- Provide joinability notes and keying guidance without producing secrets
"""

import argparse
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


DIRECT_ID_PATTERNS = [
    r"^name$", r"first_?name", r"last_?name", r"full_?name",
    r"email", r"e-?mail",
    r"phone", r"mobile",
    r"ssn", r"social_?security",
    r"passport", r"driver_?license",
    r"iban", r"bank_?account",
    r"credit_?card", r"pan$",
    r"address", r"street", r"zip", r"postal", r"postcode",
]

QUASI_ID_PATTERNS = [
    r"ip(_?address)?$", r"user_?agent", r"device_?id", r"advertising_?id",
    r"birth", r"dob", r"date_?of_?birth",
    r"lat", r"latitude", r"lon", r"lng", r"longitude",
]

SENSITIVE_PATTERNS = [
    r"diagnos", r"medical", r"health",
    r"salary", r"compensation", r"wage",
    r"religion", r"politic", r"union",
]

FREE_TEXT_PATTERNS = [r"notes", r"comment", r"description", r"message", r"free_?text"]

DATE_PATTERNS = [r"_at$", r"timestamp", r"date$", r"datetime", r"time$"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.strip().lower()).strip("_")


def _match_any(name: str, patterns: List[str]) -> bool:
    n = _norm(name)
    return any(re.search(p, n) for p in patterns)


@dataclass
class Decision:
    category: str
    transformation: str
    output_name: str
    params: Dict[str, Any]
    rationale: str


def classify_field(field: Dict[str, Any]) -> Tuple[str, List[str]]:
    name = str(field.get("name", ""))
    tags = [str(t).lower() for t in (field.get("tags") or [])]

    reasons: List[str] = []

    if "direct_identifier" in tags:
        return "direct_identifier", ["tag:direct_identifier"]
    if "quasi_identifier" in tags:
        return "quasi_identifier", ["tag:quasi_identifier"]
    if "sensitive" in tags:
        return "sensitive", ["tag:sensitive"]
    if "free_text" in tags:
        return "free_text", ["tag:free_text"]

    if _match_any(name, DIRECT_ID_PATTERNS):
        reasons.append("name_pattern:direct_identifier")
        return "direct_identifier", reasons
    if _match_any(name, FREE_TEXT_PATTERNS):
        reasons.append("name_pattern:free_text")
        return "free_text", reasons
    if _match_any(name, SENSITIVE_PATTERNS):
        reasons.append("name_pattern:sensitive")
        return "sensitive", reasons
    if _match_any(name, QUASI_ID_PATTERNS):
        reasons.append("name_pattern:quasi_identifier")
        return "quasi_identifier", reasons

    return "non_sensitive", ["default"]


def decide_transformation(field: Dict[str, Any], policy: Dict[str, Any]) -> Decision:
    name = str(field.get("name", ""))
    ftype = str(field.get("type", "string")).lower()
    join_key = bool(field.get("join_key", False))

    category, reasons = classify_field(field)

    # Determine date-like fields
    is_date_like = _match_any(name, DATE_PATTERNS) or ftype in {"date", "datetime", "timestamp"}

    reversible = bool(policy.get("reversible", False))
    allow_free_text = bool(policy.get("allow_free_text", False))

    out_name = _norm(name)
    params: Dict[str, Any] = {}

    if category == "free_text" and not allow_free_text:
        return Decision(category, "drop", out_name, {}, "High re-identification risk for free-text; default drop")

    if category == "direct_identifier":
        if join_key or policy.get("force_linkable_identifiers", False):
            if reversible:
                return Decision(category, "tokenize", out_name + "_token", {"vault": "required"}, "Reversible linkage required")
            return Decision(category, "hash", out_name + "_hash", {"method": "sha256", "salt": "required"}, "Stable linkage without reversibility")
        return Decision(category, "drop", out_name, {}, "Direct identifier not required")

    if category == "quasi_identifier":
        if join_key:
            if reversible:
                return Decision(category, "tokenize", out_name + "_token", {"vault": "required"}, "Join key requires stable token")
            return Decision(category, "hash", out_name + "_hash", {"method": "sha256", "salt": "required"}, "Join key requires stable hash")
        # Non-join quasi IDs: generalize/mask
        if "ip" in _norm(name):
            return Decision(category, "mask", out_name, {"strategy": "truncate", "keep_prefix_bits": 24}, "Reduce specificity of IP")
        if "lat" in _norm(name) or "lon" in _norm(name) or "lng" in _norm(name):
            return Decision(category, "bucket", out_name, {"precision": 2}, "Reduce location precision")
        return Decision(category, "generalize", out_name, {"strategy": "bucket"}, "Generalize quasi-identifier")

    if category == "sensitive":
        # Keep with minimization
        if is_date_like:
            return Decision(category, "shift", out_name, {"days": "per-entity-consistent"}, "Date shifting preserves intervals")
        if ftype in {"number", "integer", "float"}:
            return Decision(category, "bucket", out_name, {"strategy": "quantiles", "bins": 10}, "Bucket sensitive numeric")
        return Decision(category, "redact", out_name, {"replacement": "[REDACTED]"}, "Minimize sensitive attribute")

    # non_sensitive
    if is_date_like and policy.get("shift_dates", False):
        return Decision(category, "shift", out_name, {"days": "per-entity-consistent"}, "Optional date shifting enabled")

    return Decision(category, "keep", out_name, {}, "Not classified as identifier/sensitive")


def build_plan(schema: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    fields = schema.get("fields") or []
    if not isinstance(fields, list):
        raise ValueError("schema.fields must be a list")

    decisions: List[Decision] = []
    counts: Dict[str, int] = {
        "direct_identifier": 0,
        "quasi_identifier": 0,
        "sensitive": 0,
        "free_text": 0,
        "non_sensitive": 0,
    }

    for f in fields:
        if not isinstance(f, dict) or "name" not in f:
            raise ValueError("each field must be an object with at least a name")
        d = decide_transformation(f, policy)
        decisions.append(d)
        counts[d.category] = counts.get(d.category, 0) + 1

    notes: List[str] = []
    if any(d.transformation in {"hash", "tokenize"} for d in decisions):
        notes.append("Do not hardcode salts/keys; use a KMS/secret manager and rotate per policy.")
    if any(d.transformation == "tokenize" for d in decisions):
        notes.append("Tokenization requires a secure vault/service; restrict access and log lookups.")
    if any(d.transformation == "shift" for d in decisions):
        notes.append("Date shifting should be consistent per entity to preserve intervals; store shift offsets securely.")
    notes.append("Review for derived identifiers (e.g., combining fields can re-identify).")

    field_map = []
    for f, d in zip(fields, decisions):
        field_map.append({
            "input": f.get("name"),
            "type": f.get("type", "string"),
            "category": d.category,
            "output": d.output_name,
            "transformation": d.transformation,
            "params": d.params,
            "rationale": d.rationale,
        })

    return {
        "summary": {
            "dataset": schema.get("dataset", ""),
            "policy": policy,
            "counts_by_category": counts,
            "total_fields": len(fields),
        },
        "field_map": field_map,
        "notes": notes,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", required=True, help="Path to schema JSON")
    ap.add_argument("--out", required=True, help="Output plan JSON path")
    ap.add_argument("--reversible", action="store_true", help="Prefer reversible tokenization for linkable identifiers")
    ap.add_argument("--allow-free-text", action="store_true", help="Allow retaining free-text fields (not recommended)")
    ap.add_argument("--shift-dates", action="store_true", help="Shift non-sensitive date fields")
    args = ap.parse_args()

    with open(args.schema, "r", encoding="utf-8") as f:
        schema = json.load(f)

    policy = {
        "reversible": bool(args.reversible),
        "allow_free_text": bool(args.allow_free_text),
        "shift_dates": bool(args.shift_dates),
    }

    plan = build_plan(schema, policy)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Wrote plan to {args.out}")


if __name__ == "__main__":
    main()
