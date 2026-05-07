"""On-Call Runbook Executor.

Runs a YAML-defined runbook with prechecks, steps, and postchecks. Defaults to
dry-run; requires `--mode execute` to actually run commands. Emits a Markdown
execution log.

Usage:
  python runbook.py --runbook sample_runbook.yml                 # dry-run
  python runbook.py --runbook sample_runbook.yml --mode execute  # actually run
  python runbook.py --runbook sample_runbook.yml --mode execute --yes  # no prompts
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def load_yaml(path: str) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(open(path))
    except ImportError:
        return _mini_yaml(open(path).read())


def _mini_yaml(text: str):
    """Tiny YAML parser supporting the runbook shape."""
    import re
    lines = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    root: dict = {}

    def indent_of(s):
        return len(s) - len(s.lstrip(" "))

    i = 0

    def parse_block(base_indent: int, into):
        nonlocal i
        while i < len(lines):
            ln = lines[i]
            ind = indent_of(ln)
            if ind < base_indent:
                return
            stripped = ln.strip()
            if stripped.startswith("- "):
                if not isinstance(into, list):
                    return
                item_text = stripped[2:]
                obj: dict = {}
                if ":" in item_text:
                    k, v = item_text.split(":", 1)
                    if v.strip():
                        obj[k.strip()] = _coerce(v.strip())
                    else:
                        i += 1
                        nested: dict = {}
                        parse_block(ind + 2, nested)
                        obj[k.strip()] = nested
                        into.append(obj)
                        continue
                into.append(obj)
                i += 1
                if i < len(lines) and indent_of(lines[i]) > ind:
                    parse_block(ind + 2, obj)
                continue
            m = re.match(r"^([\w_-]+):\s*(.*)$", stripped)
            if not m:
                i += 1
                continue
            key, val = m.group(1), m.group(2)
            i += 1
            if val == "":
                # peek next non-empty line to decide list vs dict
                if i < len(lines) and lines[i].lstrip().startswith("- "):
                    new_list: list = []
                    into[key] = new_list
                    parse_block(ind + 2, new_list)
                else:
                    new_dict: dict = {}
                    into[key] = new_dict
                    parse_block(ind + 2, new_dict)
            else:
                into[key] = _coerce(val)

    parse_block(0, root)
    return root


def _coerce(v: str):
    v = v.strip()
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    try:
        return int(v)
    except ValueError:
        try:
            return float(v)
        except ValueError:
            return v


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 20] + f"\n…[truncated {len(s) - n} bytes]"


def run_cmd(cmd: str, mode: str, max_output: int) -> dict:
    started = now_utc()
    if mode == "dry-run":
        return {
            "started": started,
            "ended": started,
            "exit": None,
            "stdout": "(dry-run; not executed)",
            "stderr": "",
            "duration_ms": 0,
        }
    t0 = time.time()
    proc = subprocess.run(["/bin/sh", "-c", cmd], capture_output=True, text=True)
    duration = int((time.time() - t0) * 1000)
    return {
        "started": started,
        "ended": now_utc(),
        "exit": proc.returncode,
        "stdout": truncate(proc.stdout, max_output),
        "stderr": truncate(proc.stderr, max_output),
        "duration_ms": duration,
    }


def confirm(prompt: str, auto_yes: bool) -> bool:
    if auto_yes:
        return True
    sys.stdout.write(prompt + " [y/N]: ")
    sys.stdout.flush()
    try:
        ans = input().strip().lower()
    except EOFError:
        return False
    return ans == "y" or ans == "yes"


def run_check_block(name: str, items: list[dict], mode: str, max_output: int, log: list[str]) -> bool:
    if not items:
        return True
    log.append(f"\n## {name}")
    all_ok = True
    for c in items or []:
        log.append(f"\n### {c.get('desc') or '(no description)'}")
        log.append(f"`$ {c['cmd']}`")
        result = run_cmd(c["cmd"], mode, max_output)
        log.append(f"- exit: `{result['exit']}` · duration: `{result['duration_ms']}ms` · started `{result['started']}`")
        if result["stdout"]:
            log.append(f"```\n{result['stdout']}\n```")
        if result["stderr"]:
            log.append(f"stderr:\n```\n{result['stderr']}\n```")
        if mode == "execute" and result["exit"] not in (0, None):
            all_ok = False
            log.append(f"> ❌ check failed")
    return all_ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runbook", required=True)
    ap.add_argument("--mode", choices=["dry-run", "execute"], default="dry-run")
    ap.add_argument("--yes", action="store_true", help="Skip confirmation prompts")
    ap.add_argument("--max-output", type=int, default=4096)
    ap.add_argument("--log", default="-")
    args = ap.parse_args()

    rb = load_yaml(args.runbook)
    log = [
        f"# Runbook execution: {rb.get('name', '(unnamed)')}",
        f"- Description: {rb.get('description', '')}",
        f"- Owner: {rb.get('owner', '')}",
        f"- Mode: **{args.mode}**",
        f"- Started: {now_utc()}",
    ]

    if not run_check_block("Prechecks", rb.get("prechecks") or [], args.mode, args.max_output, log):
        log.append("\n> ⛔ Aborting: precheck failed.")
        out = "\n".join(log)
        print(out) if args.log == "-" else Path(args.log).write_text(out)
        return 1

    log.append("\n## Steps")
    failed = False
    for step in rb.get("steps") or []:
        sid = step.get("id", "")
        log.append(f"\n### Step `{sid}` — {step.get('desc', '')}")
        log.append(f"`$ {step['cmd']}`")

        if args.mode == "execute" and step.get("requires_confirm"):
            ok = confirm(f"Run step `{sid}`? cmd: {step['cmd']}", args.yes)
            if not ok:
                log.append("> Skipped by operator.")
                failed = True
                break

        result = run_cmd(step["cmd"], args.mode, args.max_output)
        log.append(f"- exit: `{result['exit']}` · duration: `{result['duration_ms']}ms` · started `{result['started']}`")
        if result["stdout"]:
            log.append(f"```\n{result['stdout']}\n```")
        if result["stderr"]:
            log.append(f"stderr:\n```\n{result['stderr']}\n```")

        if args.mode == "execute" and step.get("expect_zero_exit") and result["exit"] != 0:
            log.append("> ❌ step failed (non-zero exit).")
            failed = True
            break

    if not failed:
        run_check_block("Postchecks", rb.get("postchecks") or [], args.mode, args.max_output, log)

    log.append(f"\n## Done — {now_utc()}")
    log.append(f"- Result: **{'FAILED' if failed else 'OK'}**")

    out = "\n".join(log)
    if args.log == "-":
        print(out)
    else:
        Path(args.log).write_text(out)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
