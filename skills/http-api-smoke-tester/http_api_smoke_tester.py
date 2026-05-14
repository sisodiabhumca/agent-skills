#!/usr/bin/env python3
"""Vendor-neutral HTTP API smoke tester.

Reads a JSON plan and executes HTTP requests with basic assertions.
Stdlib-only.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


REDACT_HEADERS = {"authorization", "x-api-key"}


def _redact_headers(headers):
    out = {}
    for k, v in (headers or {}).items():
        if k.lower() in REDACT_HEADERS:
            out[k] = "<redacted>"
        else:
            out[k] = v
    return out


def _json_loads_maybe(data_bytes):
    try:
        return json.loads(data_bytes.decode("utf-8", errors="replace"))
    except Exception:
        return None


def _get_by_json_path(obj, path):
    """Very small JSONPath-like accessor: $.a.b[0].c"""
    if not path.startswith("$."):
        raise ValueError("json_path must start with '$.'")
    cur = obj
    tokens = []
    buf = ""
    i = 2
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if buf:
                tokens.append(buf)
                buf = ""
            i += 1
            continue
        if ch == "[":
            if buf:
                tokens.append(buf)
                buf = ""
            j = path.find("]", i)
            if j == -1:
                raise ValueError("Unclosed [ in json_path")
            idx = int(path[i + 1 : j])
            tokens.append(idx)
            i = j + 1
            continue
        buf += ch
        i += 1
    if buf:
        tokens.append(buf)

    for t in tokens:
        if isinstance(t, int):
            if not isinstance(cur, list) or t >= len(cur):
                return (False, None)
            cur = cur[t]
        else:
            if not isinstance(cur, dict) or t not in cur:
                return (False, None)
            cur = cur[t]
    return (True, cur)


def _assertions(step, status, headers, body_bytes):
    failures = []
    assertions = step.get("assert", [])

    body_text = body_bytes.decode("utf-8", errors="replace")
    body_json = _json_loads_maybe(body_bytes)

    for a in assertions:
        atype = a.get("type")
        if atype == "status_equals":
            exp = int(a.get("value"))
            if status != exp:
                failures.append(f"status {status} != {exp}")
        elif atype == "header_equals":
            name = a.get("name")
            exp = a.get("value")
            got = headers.get(name.lower())
            if got != exp:
                failures.append(f"header {name}='{got}' != '{exp}'")
        elif atype == "header_contains":
            name = a.get("name")
            needle = a.get("value")
            got = headers.get(name.lower(), "")
            if needle not in got:
                failures.append(f"header {name} does not contain '{needle}'")
        elif atype == "body_contains":
            needle = a.get("value", "")
            if needle not in body_text:
                failures.append(f"body does not contain '{needle}'")
        elif atype == "json_path_exists":
            if body_json is None:
                failures.append("response is not valid JSON")
            else:
                ok, _ = _get_by_json_path(body_json, a.get("path"))
                if not ok:
                    failures.append(f"missing json_path {a.get('path')}")
        elif atype == "json_path_equals":
            if body_json is None:
                failures.append("response is not valid JSON")
            else:
                ok, got = _get_by_json_path(body_json, a.get("path"))
                exp = a.get("value")
                if (not ok) or got != exp:
                    failures.append(f"json_path {a.get('path')} value '{got}' != '{exp}'")
        else:
            failures.append(f"unknown assertion type: {atype}")

    return failures


def _do_request(base_url, step, timeout_s):
    method = step.get("method", "GET").upper()
    path = step.get("path", "/")
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))

    headers = step.get("headers", {})
    data = None
    if "json" in step:
        data = json.dumps(step["json"]).encode("utf-8")
        headers = dict(headers)
        headers.setdefault("Content-Type", "application/json")
    elif "data" in step:
        # raw string
        data = str(step["data"]).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method)
    for k, v in (headers or {}).items():
        req.add_header(k, v)

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            body = resp.read()
            status = resp.getcode()
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "ok": True,
                "url": url,
                "status": status,
                "headers": resp_headers,
                "body": body,
                "duration_ms": int((time.time() - start) * 1000),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        resp_headers = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        return {
            "ok": False,
            "url": url,
            "status": int(getattr(e, "code", 0) or 0),
            "headers": resp_headers,
            "body": body,
            "duration_ms": int((time.time() - start) * 1000),
            "error": f"HTTPError: {e}",
        }
    except Exception as e:
        return {
            "ok": False,
            "url": url,
            "status": 0,
            "headers": {},
            "body": b"",
            "duration_ms": int((time.time() - start) * 1000),
            "error": f"Error: {e}",
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--body-max", type=int, default=2000)
    args = ap.parse_args()

    with open(args.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)

    base_url = plan.get("base_url")
    steps = plan.get("steps", [])
    if not isinstance(base_url, str) or not base_url:
        raise SystemExit("plan.base_url must be a non-empty string")
    if not isinstance(steps, list) or not steps:
        raise SystemExit("plan.steps must be a non-empty list")

    report_steps = []
    total_start = time.time()
    passed = True

    for idx, step in enumerate(steps):
        name = step.get("name") or f"step_{idx+1}"
        res = _do_request(base_url, step, args.timeout)
        failures = _assertions(step, res["status"], res["headers"], res["body"])

        step_passed = (len(failures) == 0)
        if not step_passed:
            passed = False

        body_preview = res["body"].decode("utf-8", errors="replace")[: args.body_max]

        report_steps.append(
            {
                "name": name,
                "passed": step_passed,
                "url": res["url"],
                "status": res["status"],
                "duration_ms": res["duration_ms"],
                "request_headers": _redact_headers(step.get("headers", {})),
                "failures": failures,
                "error": res["error"],
                "body_preview": body_preview,
            }
        )

    total_ms = int((time.time() - total_start) * 1000)
    out = {
        "passed": passed,
        "summary": {
            "steps": len(report_steps),
            "passed_steps": sum(1 for s in report_steps if s["passed"]),
            "failed_steps": sum(1 for s in report_steps if not s["passed"]),
            "total_duration_ms": total_ms,
        },
        "steps": report_steps,
    }
    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")

    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
