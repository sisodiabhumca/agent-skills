#!/usr/bin/env python3
"""Vendor-neutral data contract validator.

Validates JSON records against a simple contract (types + constraints + cross-field rules).
Supports JSON array files or JSON Lines.

Stdlib-only.
"""

import argparse
import json
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple


TYPE_MAP = {
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "object": dict,
    "array": list,
    "null": type(None),
}


def iter_records(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        first = f.read(1)
        f.seek(0)
        if first == "[":
            data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("JSON array input must be a list")
            for rec in data:
                yield rec
        else:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)


def check_type(value: Any, expected: str) -> bool:
    py = TYPE_MAP.get(expected)
    if py is None:
        return False
    # bool is subclass of int; treat carefully
    if expected in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, py)


def _add_error(errors: List[Dict[str, Any]], index: int, record_id: Any, field: str, code: str, message: str):
    errors.append(
        {
            "index": index,
            "record_id": record_id,
            "field": field,
            "code": code,
            "message": message,
        }
    )


def validate_record(index: int, rec: Any, contract: Dict[str, Any], errors: List[Dict[str, Any]]):
    record_id = None
    if isinstance(rec, dict):
        record_id = rec.get("id")
    else:
        _add_error(errors, index, None, "__record__", "not_object", "Record must be a JSON object")
        return

    fields = contract.get("fields", {})
    for fname, spec in fields.items():
        required = bool(spec.get("required", False))
        if required and fname not in rec:
            _add_error(errors, index, record_id, fname, "missing_required", "Required field is missing")
            continue
        if fname not in rec:
            continue
        val = rec.get(fname)
        expected_type = spec.get("type")
        if expected_type and not check_type(val, expected_type):
            _add_error(
                errors,
                index,
                record_id,
                fname,
                "type_mismatch",
                f"Expected type {expected_type}",
            )
            continue

        # constraints
        if isinstance(val, str):
            ml = spec.get("min_length")
            xl = spec.get("max_length")
            if ml is not None and len(val) < int(ml):
                _add_error(errors, index, record_id, fname, "min_length", f"Length < {ml}")
            if xl is not None and len(val) > int(xl):
                _add_error(errors, index, record_id, fname, "max_length", f"Length > {xl}")
            rg = spec.get("regex")
            if rg:
                if not re.search(rg, val):
                    _add_error(errors, index, record_id, fname, "regex", "Value does not match regex")

        if isinstance(val, (int, float)) and not isinstance(val, bool):
            mn = spec.get("min")
            mx = spec.get("max")
            if mn is not None and val < float(mn):
                _add_error(errors, index, record_id, fname, "min", f"Value < {mn}")
            if mx is not None and val > float(mx):
                _add_error(errors, index, record_id, fname, "max", f"Value > {mx}")

    # cross-field rules
    for rule in contract.get("rules", []) or []:
        rname = rule.get("name", "unnamed_rule")
        if_conds = rule.get("if", []) or []
        then_conds = rule.get("then", []) or []
        if all(eval_cond(rec, c) for c in if_conds):
            for c in then_conds:
                if not eval_cond(rec, c):
                    field = c.get("field", "__rule__")
                    _add_error(errors, index, record_id, field, "rule_violation", f"Rule failed: {rname}")


def eval_cond(rec: Dict[str, Any], cond: Dict[str, Any]) -> bool:
    field = cond.get("field")
    op = cond.get("op")
    value = cond.get("value")
    left = rec.get(field)

    if op == "exists":
        return field in rec and rec.get(field) is not None
    if op == "equals":
        return left == value
    if op == "not_equals":
        return left != value
    if op == "in":
        return left in (value or [])
    if op == "gte":
        try:
            return left >= value
        except Exception:
            return False
    if op == "lte":
        try:
            return left <= value
        except Exception:
            return False
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", help="Write report JSON to this file")
    args = ap.parse_args()

    with open(args.contract, "r", encoding="utf-8") as f:
        contract = json.load(f)

    errors: List[Dict[str, Any]] = []
    total = 0
    for i, rec in enumerate(iter_records(args.data)):
        total += 1
        validate_record(i, rec, contract, errors)

    report = {
        "summary": {
            "records": total,
            "errors": len(errors),
            "invalid_records": len(set(e["index"] for e in errors)),
        },
        "errors": errors,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
