#!/usr/bin/env python3
"""Vendor-neutral support macro personalizer.

Loads macros and a context variable map, validates required placeholders,
and renders ready-to-send drafts.

Stdlib-only.
"""

import argparse
import json
import os
import re
from string import Template
from typing import Any, Dict, List, Set


PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_\.]*)\}")


def extract_placeholders(text: str) -> Set[str]:
    return set(PLACEHOLDER_RE.findall(text or ""))


def to_template(text: str) -> Template:
    # Convert {var} -> ${var} for string.Template
    return Template(PLACEHOLDER_RE.sub(lambda m: "${" + m.group(1) + "}", text or ""))


def flatten_vars(d: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
    out: Dict[str, str] = {}
    for k, v in d.items():
        key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            out.update(flatten_vars(v, key))
        else:
            out[key] = str(v)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--macros_json", required=True)
    ap.add_argument("--context_json", required=True)
    ap.add_argument("--out_dir", required=True)
    ap.add_argument("--allow_missing", action="store_true", help="Allow unresolved placeholders; they will be kept as-is")
    args = ap.parse_args()

    with open(args.macros_json, "r", encoding="utf-8") as f:
        macros = json.load(f)
    with open(args.context_json, "r", encoding="utf-8") as f:
        ctx = json.load(f)

    variables = flatten_vars(ctx.get("variables") or {})

    os.makedirs(args.out_dir, exist_ok=True)

    macro_list = macros.get("macros") or []
    rendered = 0
    errors = 0

    for m in macro_list:
        mid = str(m.get("id"))
        subj_t = str(m.get("subject_template", ""))
        body_t = str(m.get("body_template", ""))
        required = set(m.get("required_variables") or [])

        placeholders = extract_placeholders(subj_t) | extract_placeholders(body_t)
        missing = sorted([p for p in (placeholders | required) if p not in variables])

        if missing and not args.allow_missing:
            errors += 1
            out = {
                "id": mid,
                "subject": None,
                "body": None,
                "missing_variables": missing,
                "error": "missing_variables",
            }
        else:
            subj = to_template(subj_t).safe_substitute(variables)
            body = to_template(body_t).safe_substitute(variables)
            out = {"id": mid, "subject": subj, "body": body, "missing_variables": missing}
            rendered += 1

        with open(os.path.join(args.out_dir, f"{mid}.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    summary = {"macros": len(macro_list), "rendered": rendered, "errors": errors, "out_dir": args.out_dir}
    print(json.dumps(summary, indent=2))
    return 0 if errors == 0 or args.allow_missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
