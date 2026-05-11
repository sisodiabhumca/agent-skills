#!/usr/bin/env python3
"""utm-campaign-governor

Validates and normalizes UTM parameters in a batch of URLs.

Input: CSV with column 'url'
Output: CSV with status/issues/normalized_url

Vendor-neutral: no assumptions about analytics platform.
"""

import argparse
import csv
import json
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


DEFAULT_POLICY = {
    "required_params": ["utm_source", "utm_medium", "utm_campaign"],
    "lowercase_values": True,
    "allowed_sources": [],
    "allowed_mediums": [],
}


def load_policy(path):
    if not path:
        return dict(DEFAULT_POLICY)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    pol = dict(DEFAULT_POLICY)
    pol.update({k: v for k, v in data.items() if v is not None})
    return pol


def normalize(url, policy):
    issues = []
    parts = urlsplit(url)
    q = parse_qsl(parts.query, keep_blank_values=True)

    # preserve order, but allow updating
    params = []
    seen = {}
    for k, v in q:
        if k in seen:
            issues.append(f"duplicate_param:{k}")
        seen[k] = v
        params.append((k, v))

    # Build dict of utm
    utm = {k: v for k, v in params if k.startswith("utm_")}

    # Required params
    missing = [p for p in policy["required_params"] if p not in utm or utm[p] == ""]
    if missing:
        issues.append("missing:" + ",".join(missing))

    # Allowed lists
    src = utm.get("utm_source")
    med = utm.get("utm_medium")
    if policy.get("allowed_sources") and src and src not in policy["allowed_sources"]:
        issues.append("bad_utm_source")
    if policy.get("allowed_mediums") and med and med not in policy["allowed_mediums"]:
        issues.append("bad_utm_medium")

    # Normalization (values only)
    fixed = False
    if policy.get("lowercase_values"):
        new_params = []
        for k, v in params:
            if k.startswith("utm_"):
                nv = v.lower()
                if nv != v:
                    fixed = True
                new_params.append((k, nv))
            else:
                new_params.append((k, v))
        params = new_params

    normalized_query = urlencode(params, doseq=True)
    normalized_url = urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment))

    if missing:
        status = "invalid"
        normalized_url = ""
    else:
        status = "fixed" if fixed or issues else "ok"

    return status, ";".join(issues), normalized_url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--policy")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    policy = load_policy(args.policy)

    with open(args.input, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "url" not in reader.fieldnames:
            raise SystemExit("Input CSV must contain a 'url' column")
        rows = list(reader)

    out_rows = []
    for r in rows:
        url = (r.get("url") or "").strip()
        status, issues, normalized_url = normalize(url, policy)
        out_rows.append(
            {"url": url, "status": status, "issues": issues, "normalized_url": normalized_url}
        )

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "status", "issues", "normalized_url"])
        writer.writeheader()
        writer.writerows(out_rows)

    ok = sum(1 for r in out_rows if r["status"] == "ok")
    fixed = sum(1 for r in out_rows if r["status"] == "fixed")
    invalid = sum(1 for r in out_rows if r["status"] == "invalid")
    print(f"Processed {len(out_rows)} URLs: ok={ok} fixed={fixed} invalid={invalid}")


if __name__ == "__main__":
    main()
