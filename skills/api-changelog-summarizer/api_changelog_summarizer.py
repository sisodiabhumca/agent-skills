#!/usr/bin/env python3
"""Vendor-neutral OpenAPI changelog summarizer (JSON only).

Creates a human-readable summary of breaking and non-breaking changes between
two OpenAPI specs.

Stdlib-only.
"""

import argparse
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple


HTTP_METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def op_map(spec: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    m: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.lower() in HTTP_METHODS and isinstance(op, dict):
                m[(method.lower(), path)] = op
    return m


def get_params(op: Dict[str, Any]) -> List[Dict[str, Any]]:
    params = op.get("parameters") or []
    return [p for p in params if isinstance(p, dict)]


def param_key(p: Dict[str, Any]) -> Tuple[str, str]:
    return (str(p.get("in", "")), str(p.get("name", "")))


def required_param_set(op: Dict[str, Any]) -> Set[Tuple[str, str]]:
    s = set()
    for p in get_params(op):
        if p.get("required") is True:
            s.add(param_key(p))
    return s


def all_param_set(op: Dict[str, Any]) -> Set[Tuple[str, str]]:
    return {param_key(p) for p in get_params(op)}


def request_body_required(op: Dict[str, Any]) -> bool:
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return False
    return rb.get("required") is True


def response_code_set(op: Dict[str, Any]) -> Set[str]:
    resp = op.get("responses") or {}
    if not isinstance(resp, dict):
        return set()
    return {str(code) for code in resp.keys()}


@dataclass
class Diff:
    breaking: List[str]
    non_breaking: List[str]
    notes: List[str]


def diff_specs(old: Dict[str, Any], new: Dict[str, Any]) -> Diff:
    old_ops = op_map(old)
    new_ops = op_map(new)

    breaking: List[str] = []
    non_breaking: List[str] = []

    for k in sorted(old_ops.keys() - new_ops.keys()):
        method, path = k
        breaking.append(f"Removed operation: `{method.upper()} {path}`")

    for k in sorted(new_ops.keys() - old_ops.keys()):
        method, path = k
        non_breaking.append(f"Added operation: `{method.upper()} {path}`")

    for k in sorted(old_ops.keys() & new_ops.keys()):
        old_op = old_ops[k]
        new_op = new_ops[k]
        method, path = k
        label = f"`{method.upper()} {path}`"

        old_all = all_param_set(old_op)
        new_all = all_param_set(new_op)
        old_req = required_param_set(old_op)
        new_req = required_param_set(new_op)

        for p in sorted(old_all - new_all):
            # Removing a parameter can be breaking if clients relied on it, but
            # we conservatively label as breaking only if it was required.
            if p in old_req:
                breaking.append(f"{label}: removed required parameter {p}")
            else:
                non_breaking.append(f"{label}: removed optional parameter {p}")

        for p in sorted(new_all - old_all):
            if p in new_req:
                breaking.append(f"{label}: added required parameter {p}")
            else:
                non_breaking.append(f"{label}: added optional parameter {p}")

        for p in sorted(old_req - new_req):
            non_breaking.append(f"{label}: parameter became optional {p}")

        for p in sorted(new_req - old_req):
            breaking.append(f"{label}: parameter became required {p}")

        if request_body_required(old_op) is False and request_body_required(new_op) is True:
            breaking.append(f"{label}: requestBody became required")
        if request_body_required(old_op) is True and request_body_required(new_op) is False:
            non_breaking.append(f"{label}: requestBody became optional")

        old_codes = response_code_set(old_op)
        new_codes = response_code_set(new_op)
        for c in sorted(old_codes - new_codes):
            breaking.append(f"{label}: removed response code `{c}`")
        for c in sorted(new_codes - old_codes):
            non_breaking.append(f"{label}: added response code `{c}`")

    notes = [
        "Schema-level compatibility is not fully analyzed (e.g., type widening/narrowing).",
        "Only OpenAPI JSON inputs are supported by the reference implementation.",
    ]
    return Diff(breaking=breaking, non_breaking=non_breaking, notes=notes)


def render_md(d: Diff, old_path: str, new_path: str) -> str:
    lines: List[str] = []
    lines.append("# API changelog")
    lines.append("")
    lines.append(f"Compared `{old_path}` → `{new_path}`")
    lines.append("")

    lines.append("## Breaking changes")
    if d.breaking:
        for item in d.breaking:
            lines.append(f"- {item}")
    else:
        lines.append("- None detected")
    lines.append("")

    lines.append("## Non-breaking changes")
    if d.non_breaking:
        for item in d.non_breaking:
            lines.append(f"- {item}")
    else:
        lines.append("- None detected")
    lines.append("")

    lines.append("## Notes / limitations")
    for n in d.notes:
        lines.append(f"- {n}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old_spec", required=True)
    ap.add_argument("--new_spec", required=True)
    ap.add_argument("--out_md", required=True)
    args = ap.parse_args()

    old = load_json(args.old_spec)
    new = load_json(args.new_spec)
    d = diff_specs(old, new)
    md = render_md(d, args.old_spec, args.new_spec)

    with open(args.out_md, "w", encoding="utf-8") as f:
        f.write(md)

    print(json.dumps({"out_md": args.out_md, "breaking": len(d.breaking), "non_breaking": len(d.non_breaking)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
