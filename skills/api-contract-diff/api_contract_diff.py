#!/usr/bin/env python3
import argparse
import json
from typing import Any, Dict, List, Optional, Tuple


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get(d: Dict[str, Any], *keys, default=None):
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def _ops(spec: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    paths = spec.get("paths", {})
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if not isinstance(paths, dict):
        return out
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            m = str(method).lower()
            if m not in {"get", "post", "put", "patch", "delete", "head", "options", "trace"}:
                continue
            if isinstance(op, dict):
                out[(str(path), m)] = op
    return out


def _param_key(p: Dict[str, Any]) -> Tuple[str, str]:
    return (str(p.get("in", "")), str(p.get("name", "")))


def _collect_params(op: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    params = op.get("parameters", [])
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if isinstance(params, list):
        for p in params:
            if isinstance(p, dict):
                out[_param_key(p)] = p
    return out


def _required_props(schema: Any) -> List[str]:
    if not isinstance(schema, dict):
        return []
    req = schema.get("required", [])
    if isinstance(req, list):
        return [str(x) for x in req if isinstance(x, (str, int, float))]
    return []


def _json_schema_from_request_body(op: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return None
    content = rb.get("content")
    if not isinstance(content, dict):
        return None
    app_json = content.get("application/json")
    if not isinstance(app_json, dict):
        return None
    schema = app_json.get("schema")
    return schema if isinstance(schema, dict) else None


def _responses(op: Dict[str, Any]) -> List[str]:
    r = op.get("responses", {})
    if not isinstance(r, dict):
        return []
    return sorted([str(k) for k in r.keys()])


def _add_change(bucket: List[Dict[str, Any]], kind: str, location: str, details: Dict[str, Any]):
    bucket.append({"kind": kind, "location": location, "details": details})


def compare(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    old_ops = _ops(old)
    new_ops = _ops(new)

    breaking: List[Dict[str, Any]] = []
    non_breaking: List[Dict[str, Any]] = []
    unknown: List[Dict[str, Any]] = []

    old_keys = set(old_ops.keys())
    new_keys = set(new_ops.keys())

    for k in sorted(old_keys - new_keys):
        path, method = k
        _add_change(breaking, "operation_removed", f"{method.upper()} {path}", {})

    for k in sorted(new_keys - old_keys):
        path, method = k
        _add_change(non_breaking, "operation_added", f"{method.upper()} {path}", {})

    for k in sorted(old_keys & new_keys):
        path, method = k
        old_op = old_ops[k]
        new_op = new_ops[k]
        loc = f"{method.upper()} {path}"

        # parameters
        old_params = _collect_params(old_op)
        new_params = _collect_params(new_op)
        for pk in sorted(old_params.keys() - new_params.keys()):
            _add_change(breaking, "parameter_removed", loc, {"param_in": pk[0], "name": pk[1]})
        for pk in sorted(new_params.keys() - old_params.keys()):
            p = new_params[pk]
            required = bool(p.get("required", False))
            bucket = breaking if required else non_breaking
            _add_change(bucket, "parameter_added", loc, {"param_in": pk[0], "name": pk[1], "required": required})

        # requestBody requiredness
        old_rb = old_op.get("requestBody") if isinstance(old_op.get("requestBody"), dict) else None
        new_rb = new_op.get("requestBody") if isinstance(new_op.get("requestBody"), dict) else None
        old_rb_req = bool(old_rb.get("required", False)) if old_rb else False
        new_rb_req = bool(new_rb.get("required", False)) if new_rb else False
        if old_rb_req != new_rb_req:
            if new_rb_req and not old_rb_req:
                _add_change(breaking, "request_body_now_required", loc, {})
            else:
                _add_change(non_breaking, "request_body_no_longer_required", loc, {})

        # required properties in JSON request schema
        old_schema = _json_schema_from_request_body(old_op)
        new_schema = _json_schema_from_request_body(new_op)
        old_req = set(_required_props(old_schema))
        new_req = set(_required_props(new_schema))
        for p in sorted(old_req - new_req):
            _add_change(non_breaking, "request_required_property_removed", loc, {"property": p})
        for p in sorted(new_req - old_req):
            _add_change(breaking, "request_required_property_added", loc, {"property": p})

        # responses
        old_resp = set(_responses(old_op))
        new_resp = set(_responses(new_op))
        for code in sorted(old_resp - new_resp):
            _add_change(breaking, "response_removed", loc, {"status": code})
        for code in sorted(new_resp - old_resp):
            _add_change(non_breaking, "response_added", loc, {"status": code})

        # heuristic: schema present removed/added
        if old_schema and not new_schema:
            _add_change(unknown, "request_schema_removed", loc, {})
        if not old_schema and new_schema:
            _add_change(unknown, "request_schema_added", loc, {})

    report = {
        "summary": {
            "breaking": len(breaking),
            "non_breaking": len(non_breaking),
            "unknown_risk": len(unknown),
            "operations_old": len(old_ops),
            "operations_new": len(new_ops),
        },
        "breaking_changes": breaking,
        "non_breaking_changes": non_breaking,
        "unknown_risk_changes": unknown,
    }
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", required=False)
    args = ap.parse_args()

    old = _load_json(args.old)
    new = _load_json(args.new)
    report = compare(old, new)

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
