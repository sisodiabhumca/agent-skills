"""AI Eval Regression Tester.

Runs an eval suite over a candidate runner and grades outputs.

Candidate runner: a Python module exposing `run(case_input: str) -> str`.

Usage:
  python run_eval.py --suite suite.yml --runner runners.echo:run \
      --baseline baseline.jsonl --threshold 0.9 --tag-threshold refund=0.95
"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def load_yaml(path: str):
    try:
        import yaml  # type: ignore
        return yaml.safe_load(open(path))
    except ImportError:
        return _mini_yaml(open(path).read())


def _mini_yaml(text: str):
    # Minimal YAML supporting the demo suite shape.
    cases = []
    cur = None
    cur_key = None
    indent_stack = []

    lines = text.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))
        if stripped.startswith("- "):
            if cur is not None:
                cases.append(cur)
            cur = {}
            stripped = stripped[2:]
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                cur[k.strip()] = _coerce(v.strip())
            i += 1
            continue
        if cur is None:
            i += 1
            continue
        if ":" in stripped:
            k, v = stripped.split(":", 1)
            k = k.strip()
            v = v.strip()
            if v == "":
                # Look ahead to capture nested list/dict
                children = []
                j = i + 1
                base_indent = indent
                while j < len(lines):
                    nraw = lines[j]
                    if not nraw.strip():
                        j += 1
                        continue
                    nind = len(nraw) - len(nraw.lstrip(" "))
                    if nind <= base_indent:
                        break
                    children.append(nraw)
                    j += 1
                if children and children[0].lstrip().startswith("- "):
                    cur[k] = _parse_list(children)
                else:
                    cur[k] = _parse_dict(children)
                i = j
                continue
            cur[k] = _coerce(v)
        i += 1
    if cur is not None:
        cases.append(cur)
    return cases


def _parse_list(lines):
    out = []
    items = []
    base = None
    cur_block = []
    for ln in lines:
        if ln.lstrip().startswith("- "):
            if cur_block:
                items.append(cur_block)
            cur_block = [ln]
        else:
            cur_block.append(ln)
    if cur_block:
        items.append(cur_block)
    for blk in items:
        first = blk[0].lstrip()[2:].rstrip()
        if ":" in first:
            d = {}
            k, v = first.split(":", 1)
            d[k.strip()] = _coerce(v.strip())
            for ln in blk[1:]:
                s = ln.strip()
                if ":" in s:
                    k2, v2 = s.split(":", 1)
                    d[k2.strip()] = _coerce(v2.strip())
            out.append(d)
        else:
            out.append(_coerce(first))
    return out


def _parse_dict(lines):
    d = {}
    for ln in lines:
        s = ln.strip()
        if ":" in s:
            k, v = s.split(":", 1)
            d[k.strip()] = _coerce(v.strip())
    return d


def _coerce(v):
    if isinstance(v, list):
        return v
    if v == "":
        return None
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_coerce(x.strip().strip('"').strip("'")) for x in inner.split(",")]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v.strip('"').strip("'")


# -------- Graders --------

def grade_contains(output: str, values) -> tuple[bool, str]:
    missing = [v for v in values if v.lower() not in output.lower()]
    return (len(missing) == 0, f"missing: {missing}" if missing else "ok")


def grade_not_contains(output: str, values) -> tuple[bool, str]:
    found = [v for v in values if v.lower() in output.lower()]
    return (len(found) == 0, f"banned present: {found}" if found else "ok")


def grade_regex(output: str, pattern: str) -> tuple[bool, str]:
    return (bool(re.search(pattern, output, flags=re.IGNORECASE)), f"pattern={pattern}")


def grade_json_schema(output: str, schema: dict) -> tuple[bool, str]:
    try:
        obj = json.loads(output)
    except Exception as e:
        return (False, f"not JSON: {e}")
    required = schema.get("required") or []
    missing = [k for k in required if k not in obj]
    if missing:
        return (False, f"missing keys: {missing}")
    return (True, "ok")


GRADERS = {
    "contains": grade_contains,
    "not_contains": grade_not_contains,
    "regex": grade_regex,
    "json_schema": grade_json_schema,
}


def grade_case(case: dict, output: str) -> list[dict]:
    out = []
    for g in case.get("graders") or []:
        gtype = g.get("type")
        try:
            if gtype == "contains":
                passed, info = grade_contains(output, g.get("values") or [])
            elif gtype == "not_contains":
                passed, info = grade_not_contains(output, g.get("values") or [])
            elif gtype == "regex":
                passed, info = grade_regex(output, g.get("pattern", ""))
            elif gtype == "json_schema":
                passed, info = grade_json_schema(output, g.get("schema") or {})
            else:
                passed, info = (False, f"unknown grader {gtype}")
        except Exception as e:
            passed, info = (False, f"grader error: {e}")
        out.append({"type": gtype, "pass": passed, "info": info})
    return out


def load_runner(spec: str):
    mod_name, _, fn_name = spec.partition(":")
    sys.path.insert(0, str(Path.cwd()))
    mod = importlib.import_module(mod_name)
    return getattr(mod, fn_name)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--runner", required=True, help="module:function")
    ap.add_argument("--baseline", default=None, help="JSONL of prior outputs")
    ap.add_argument("--threshold", type=float, default=0.9, help="Overall pass rate to require")
    ap.add_argument("--tag-threshold", action="append", default=[], help="tag=rate")
    ap.add_argument("--out", default="results.jsonl")
    ap.add_argument("--report", default="report.md")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    cases = load_yaml(args.suite) or []
    runner = load_runner(args.runner)

    baseline_by_id: dict[str, str] = {}
    if args.baseline and Path(args.baseline).exists():
        for line in Path(args.baseline).read_text().splitlines():
            if not line.strip():
                continue
            o = json.loads(line)
            baseline_by_id[o.get("id", "")] = o.get("output", "")

    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(runner, c["input"]): c for c in cases}
        for fut in as_completed(futs):
            c = futs[fut]
            try:
                output = fut.result()
            except Exception as e:
                output = f"<runner_error: {e}>"
            grades = grade_case(c, output)
            passed = all(g["pass"] for g in grades)
            results.append({
                "id": c.get("id", ""),
                "tags": c.get("tags", []),
                "input": c["input"],
                "output": output,
                "grades": grades,
                "pass": passed,
                "diff_vs_baseline": (output != baseline_by_id.get(c.get("id", ""), output)) if baseline_by_id else False,
            })

    Path(args.out).write_text("\n".join(json.dumps(r) for r in results))

    total = len(results)
    passed = sum(1 for r in results if r["pass"])
    rate = (passed / total) if total else 0
    by_tag = defaultdict(lambda: [0, 0])
    for r in results:
        for t in r["tags"] or []:
            by_tag[t][0] += int(bool(r["pass"]))
            by_tag[t][1] += 1

    lines = [
        "# Eval Run", "",
        f"- **Cases:** {total}",
        f"- **Passed:** {passed}",
        f"- **Pass rate:** {rate*100:.1f}%",
        f"- **Threshold:** {args.threshold*100:.1f}%",
        "",
        "## By tag",
        "| Tag | Pass | Total | Rate |",
        "|---|---|---|---|",
    ]
    for tag, (p, t) in sorted(by_tag.items()):
        lines.append(f"| {tag} | {p} | {t} | {p/t*100:.1f}% |")

    lines += ["", "## Failing cases"]
    for r in results:
        if not r["pass"]:
            why = "; ".join(g["info"] for g in r["grades"] if not g["pass"])
            lines.append(f"- `{r['id']}` — {why}")

    Path(args.report).write_text("\n".join(lines))
    print(Path(args.report).read_text())

    # Gating
    fail = rate < args.threshold
    for spec in args.tag_threshold:
        if "=" not in spec:
            continue
        tag, val = spec.split("=", 1)
        if tag in by_tag:
            p, t = by_tag[tag]
            if t and (p / t) < float(val):
                fail = True
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
