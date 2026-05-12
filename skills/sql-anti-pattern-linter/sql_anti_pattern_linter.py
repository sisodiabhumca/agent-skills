#!/usr/bin/env python3
"""Vendor-neutral SQL anti-pattern linter.

Heuristic linting of SQL text to flag common performance and correctness risks.
Stdlib-only.
"""

import argparse
import json
import re
from typing import Dict, List, Optional, Tuple


RULES = [
    {
        "id": "select_star",
        "severity": "medium",
        "pattern": re.compile(r"\bselect\s+\*\b", re.IGNORECASE),
        "message": "Avoid SELECT *; specify needed columns to reduce I/O and schema-coupling.",
    },
    {
        "id": "leading_wildcard_like",
        "severity": "high",
        "pattern": re.compile(r"\blike\s+'%[^']*'", re.IGNORECASE),
        "message": "Leading-wildcard LIKE can prevent index use; consider full-text search or trigram indexes.",
    },
    {
        "id": "implicit_join",
        "severity": "medium",
        "pattern": re.compile(r"\bfrom\s+[^;\n]+,\s*[^;\n]+", re.IGNORECASE),
        "message": "Implicit joins (FROM a, b) are error-prone; use explicit JOIN ... ON ...",
    },
    {
        "id": "not_in_subquery",
        "severity": "high",
        "pattern": re.compile(r"\bnot\s+in\s*\(\s*select\b", re.IGNORECASE),
        "message": "NOT IN (subquery) can behave unexpectedly with NULLs; consider NOT EXISTS.",
    },
    {
        "id": "update_delete_without_where",
        "severity": "critical",
        "pattern": re.compile(r"\b(update|delete)\b(?![^;]*\bwhere\b)", re.IGNORECASE | re.DOTALL),
        "message": "UPDATE/DELETE without WHERE may affect all rows; double-check intent.",
    },
]

FUNC_ON_COL_RE = re.compile(r"\b(where|and|or)\b[^;\n]*\b(lower|upper|trim|substr|substring|date)\s*\(\s*([a-zA-Z_][a-zA-Z0-9_\.]*)\s*\)", re.IGNORECASE)
OR_CHAIN_RE = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_\.]*)\s*=\s*[^\s]+\s+or\s+\1\s*=", re.IGNORECASE)


def line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql_file", required=True)
    ap.add_argument("--out_json", required=True)
    args = ap.parse_args()

    with open(args.sql_file, "r", encoding="utf-8") as f:
        sql = f.read()

    findings: List[Dict[str, object]] = []

    for r in RULES:
        m = r["pattern"].search(sql)
        if m:
            findings.append(
                {
                    "rule_id": r["id"],
                    "severity": r["severity"],
                    "message": r["message"],
                    "line": line_of(sql, m.start()),
                }
            )

    for m in FUNC_ON_COL_RE.finditer(sql):
        findings.append(
            {
                "rule_id": "function_on_column",
                "severity": "medium",
                "message": f"Function applied to column '{m.group(3)}' in predicate; may be non-sargable.",
                "line": line_of(sql, m.start()),
            }
        )

    m = OR_CHAIN_RE.search(sql)
    if m:
        findings.append(
            {
                "rule_id": "or_chain",
                "severity": "low",
                "message": f"OR chain on '{m.group(1)}'; consider IN (...) for readability and plan stability.",
                "line": line_of(sql, m.start()),
            }
        )

    out = {"file": args.sql_file, "findings": findings}
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(json.dumps({"out_json": args.out_json, "findings": len(findings)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
