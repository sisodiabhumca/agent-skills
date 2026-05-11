#!/usr/bin/env python3
"""json-schema-drift-detector

Detects drift between two JSON Schema documents.

Focuses on vendor-neutral, commonly used keywords:
- type
- required
- enum
- properties

Limitations: does not fully evaluate anyOf/oneOf/allOf/$ref.
"""

import argparse
import json
import sys
from copy import deepcopy


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _norm_types(t):
    if t is None:
        return None
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return sorted([x for x in t if isinstance(x, str)])
    return None


def _get_required(schema):
    req = schema.get("required", [])
    return sorted(req) if isinstance(req, list) else []


def _index(schema, base_path=""):
    """Return mapping path -> info dict."""
    info = {}

    stype = _norm_types(schema.get("type"))
    enum = schema.get("enum")
    enum_norm = sorted(enum) if isinstance(enum, list) else None

    entry = {
        "type": stype,
        "required": _get_required(schema),
        "enum": enum_norm,
        "title": schema.get("title"),
        "description": schema.get("description"),
    }
    info[base_path or "/"] = entry

    # Object properties
    props = schema.get("properties")
    if isinstance(props, dict):
        for k, v in props.items():
            if isinstance(v, dict):
                child_path = (base_path or "") + "/" + k
                info.update(_index(v, child_path))

    return info


def _classify_change(path, old, new):
    # Added or removed
    if old is None and new is not None:
        # If field itself is required in new parent's required list, we can't infer here.
        return "non_breaking", "added"
    if old is not None and new is None:
        return "breaking", "removed"

    # Modified
    # type change
    if old.get("type") != new.get("type") and (old.get("type") or new.get("type")):
        return "breaking", "type_changed"

    # enum changes
    oenum, nenum = old.get("enum"), new.get("enum")
    if oenum is not None or nenum is not None:
        if oenum is None and nenum is not None:
            return "unknown", "enum_added"
        if oenum is not None and nenum is None:
            return "unknown", "enum_removed"
        if oenum is not None and nenum is not None:
            oset, nset = set(oenum), set(nenum)
            if nset < oset:
                return "breaking", "enum_narrowed"
            if nset > oset:
                return "non_breaking", "enum_widened"

    # required list on object nodes
    oreq, nreq = set(old.get("required") or []), set(new.get("required") or [])
    if nreq > oreq:
        return "breaking", "required_added"
    if nreq < oreq:
        return "non_breaking", "required_removed"

    # title/description only
    if (
        old.get("title") != new.get("title")
        or old.get("description") != new.get("description")
    ):
        return "non_breaking", "metadata_changed"

    return "unknown", "modified"


def diff(old_schema, new_schema):
    old_idx = _index(old_schema)
    new_idx = _index(new_schema)

    paths = sorted(set(old_idx.keys()) | set(new_idx.keys()))

    report = {"summary": {}, "breaking": [], "non_breaking": [], "unknown": []}

    for p in paths:
        o = old_idx.get(p)
        n = new_idx.get(p)
        if o == n:
            continue
        bucket, change_type = _classify_change(p, o, n)
        reason = change_type
        report[bucket].append(
            {
                "path": p,
                "change_type": change_type,
                "old": deepcopy(o),
                "new": deepcopy(n),
                "reason": reason,
            }
        )

    report["summary"] = {
        "breaking": len(report["breaking"]),
        "non_breaking": len(report["non_breaking"]),
        "unknown": len(report["unknown"]),
        "total_changes": len(report["breaking"]) + len(report["non_breaking"]) + len(report["unknown"]),
    }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    old_schema = _load_json(args.old)
    new_schema = _load_json(args.new)

    rep = diff(old_schema, new_schema)

    print(
        "Summary: total={total_changes} breaking={breaking} non_breaking={non_breaking} unknown={unknown}".format(
            **rep["summary"]
        )
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
