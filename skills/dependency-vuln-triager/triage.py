"""Dependency vulnerability triager.

Reads scanner JSON (npm audit / pip-audit / OSV / generic list) and produces a
ranked Markdown action list + a JSON file for tooling.

Usage:
    python triage.py --input sample_audit.json --out-md TRIAGE.md --out-json triage.json
    python triage.py --input npm.json --reachable reachable.txt --prod-only

Stdlib only. Vendor-neutral.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any

SEVERITY_WEIGHT = {"critical": 10, "high": 7, "moderate": 4, "medium": 4, "low": 1, "none": 0, "unknown": 1}


@dataclass
class Finding:
    id: str
    package: str
    installed: str = ""
    severity: str = "unknown"
    cvss: float = 0.0
    fix_version: str = ""
    dev_only: bool = False
    summary: str = ""
    score: float = 0.0
    reachable: bool = False


def detect_and_load(data: Any) -> list[Finding]:
    # npm audit v7+ has top-level "vulnerabilities" object keyed by package.
    if isinstance(data, dict) and "vulnerabilities" in data and isinstance(data["vulnerabilities"], dict):
        return _from_npm(data["vulnerabilities"])
    # pip-audit JSON has top-level "dependencies" list.
    if isinstance(data, dict) and "dependencies" in data and isinstance(data["dependencies"], list):
        return _from_pip_audit(data["dependencies"])
    # OSV-Scanner has "results" -> "packages" -> "vulnerabilities".
    if isinstance(data, dict) and "results" in data:
        return _from_osv(data["results"])
    # Generic flat list.
    if isinstance(data, list):
        return _from_generic(data)
    raise ValueError("Unrecognized scanner format. Expected npm/pip-audit/OSV/generic JSON.")


def _from_npm(vulns: dict) -> list[Finding]:
    out: list[Finding] = []
    for pkg, v in vulns.items():
        sev = (v.get("severity") or "unknown").lower()
        installed = ""
        # npm audit output structure varies; try common paths.
        via = v.get("via") or []
        ids: list[str] = []
        summary = ""
        for item in via:
            if isinstance(item, dict):
                if "source" in item:
                    ids.append(f"GHSA/{item['source']}")
                if not summary and item.get("title"):
                    summary = item["title"]
        fix = ""
        fa = v.get("fixAvailable")
        if isinstance(fa, dict):
            fix = fa.get("version", "") or ""
        elif fa is True:
            fix = "available"
        out.append(Finding(
            id=ids[0] if ids else f"npm:{pkg}",
            package=pkg,
            installed=installed,
            severity=sev,
            fix_version=fix,
            dev_only=bool(v.get("isDirect") is False and "dev" in (v.get("nodes") or [""])[0]),
            summary=summary or f"{pkg} vulnerability",
        ))
    return out


def _from_pip_audit(deps: list) -> list[Finding]:
    out: list[Finding] = []
    for d in deps:
        name = d.get("name", "")
        installed = d.get("version", "")
        for vuln in d.get("vulns", []) or []:
            fix = ""
            fix_versions = vuln.get("fix_versions") or []
            if fix_versions:
                fix = fix_versions[0]
            out.append(Finding(
                id=vuln.get("id", "pip:unknown"),
                package=name,
                installed=installed,
                severity=(vuln.get("severity") or "unknown").lower(),
                fix_version=fix,
                summary=vuln.get("description", "")[:200] or f"{name} vulnerability",
            ))
    return out


def _from_osv(results: list) -> list[Finding]:
    out: list[Finding] = []
    for res in results:
        for pkg in res.get("packages", []) or []:
            info = pkg.get("package", {})
            name = info.get("name", "")
            version = info.get("version", "")
            for v in pkg.get("vulnerabilities", []) or []:
                # severity from `database_specific` or `severity`
                sev = "unknown"
                cvss = 0.0
                for s in v.get("severity", []) or []:
                    if s.get("type", "").upper().startswith("CVSS"):
                        try:
                            cvss = float(s.get("score", "0").split("/")[0].split(":")[-1])
                        except Exception:
                            pass
                ds = (v.get("database_specific") or {}).get("severity", "")
                if isinstance(ds, str) and ds:
                    sev = ds.lower()
                elif cvss >= 9:
                    sev = "critical"
                elif cvss >= 7:
                    sev = "high"
                elif cvss >= 4:
                    sev = "medium"
                elif cvss > 0:
                    sev = "low"
                # fix version: first "fixed" event
                fix = ""
                for aff in v.get("affected", []) or []:
                    for r in aff.get("ranges", []) or []:
                        for ev in r.get("events", []) or []:
                            if "fixed" in ev:
                                fix = ev["fixed"]
                                break
                        if fix:
                            break
                    if fix:
                        break
                out.append(Finding(
                    id=v.get("id", "OSV-unknown"),
                    package=name,
                    installed=version,
                    severity=sev,
                    cvss=cvss,
                    fix_version=fix,
                    summary=v.get("summary", "")[:200] or f"{name} vulnerability",
                ))
    return out


def _from_generic(rows: list) -> list[Finding]:
    out = []
    for r in rows:
        out.append(Finding(
            id=str(r.get("id", "")),
            package=str(r.get("package", "")),
            installed=str(r.get("installed", "")),
            severity=str(r.get("severity", "unknown")).lower(),
            cvss=float(r.get("cvss", 0) or 0),
            fix_version=str(r.get("fix_version", "")),
            dev_only=bool(r.get("dev_only", False)),
            summary=str(r.get("summary", "")),
        ))
    return out


def score(f: Finding, reachable_pkgs: set[str], prod_only: bool) -> float:
    s = float(SEVERITY_WEIGHT.get(f.severity, 1))
    if f.cvss >= 7 and s < 7:
        s = max(s, 7.0)
    if f.fix_version:
        s += 3
    if f.package in reachable_pkgs:
        s += 2
        f.reachable = True
    if prod_only and f.dev_only:
        s -= 5
    return s


def version_key(v: str) -> tuple:
    # crude semver-ish sort: split on dots and digits
    parts = []
    for chunk in v.replace("v", "").split("."):
        n = ""
        for ch in chunk:
            if ch.isdigit():
                n += ch
            else:
                break
        parts.append(int(n) if n else 0)
    return tuple(parts) if parts else (0,)


def group_and_render(findings: list[Finding]) -> tuple[str, list[dict]]:
    # group by package
    groups: dict[str, list[Finding]] = {}
    for f in findings:
        groups.setdefault(f.package, []).append(f)

    rows: list[dict] = []
    for pkg, items in groups.items():
        max_sev = max(items, key=lambda x: SEVERITY_WEIGHT.get(x.severity, 0)).severity
        max_score = max(f.score for f in items)
        fixes = [f.fix_version for f in items if f.fix_version and f.fix_version != "available"]
        chosen_fix = max(fixes, key=version_key) if fixes else ("available" if any(f.fix_version == "available" for f in items) else "")
        installed = next((f.installed for f in items if f.installed), "")
        all_dev = all(f.dev_only for f in items)
        any_reachable = any(f.reachable for f in items)
        rows.append({
            "package": pkg,
            "installed": installed,
            "fix_version": chosen_fix,
            "max_severity": max_sev,
            "max_score": round(max_score, 1),
            "cve_count": len(items),
            "dev_only": all_dev,
            "reachable": any_reachable,
            "ids": [f.id for f in items],
        })

    rows.sort(key=lambda r: r["max_score"], reverse=True)

    def bucket(r: dict) -> str:
        if r["max_severity"] == "critical" or r["max_score"] >= 12:
            return "P0 — fix this week"
        if r["max_severity"] in {"high"} or r["max_score"] >= 8:
            return "P1 — fix this sprint"
        return "P2 — backlog"

    by_bucket: dict[str, list[dict]] = {}
    skipped: list[dict] = []
    for r in rows:
        if not r["fix_version"]:
            skipped.append({**r, "reason": "no fix available"})
            continue
        if r["dev_only"]:
            skipped.append({**r, "reason": "dev-only dependency"})
            continue
        by_bucket.setdefault(bucket(r), []).append(r)

    lines: list[str] = ["# Dependency Vulnerability Triage", ""]
    summary = (
        f"**{len(findings)}** findings across **{len(groups)}** package(s); "
        f"{sum(len(v) for v in by_bucket.values())} actionable, {len(skipped)} skipped."
    )
    lines += [summary, ""]

    for label in ["P0 — fix this week", "P1 — fix this sprint", "P2 — backlog"]:
        items = by_bucket.get(label, [])
        if not items:
            continue
        lines += [f"## {label}", ""]
        for r in items:
            reach = " · reachable" if r["reachable"] else ""
            installed = r["installed"] or "?"
            lines.append(
                f"- **{r['package']}** {installed} → {r['fix_version']} "
                f"(resolves {r['cve_count']} CVE(s), max {r['max_severity']}{reach}) "
                f"— {', '.join(r['ids'][:3])}{'…' if len(r['ids']) > 3 else ''}"
            )
        lines.append("")

    if skipped:
        lines += ["## Skipped (dev-only / no fix available)", ""]
        for r in skipped:
            lines.append(
                f"- {r['package']} ({r['max_severity']}, {r['cve_count']} CVE) — {r['reason']}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n", rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, help="Scanner JSON file")
    p.add_argument("--reachable", help="Optional text file with one reachable package per line")
    p.add_argument("--prod-only", action="store_true")
    p.add_argument("--out-md", default="TRIAGE.md")
    p.add_argument("--out-json", default="triage.json")
    args = p.parse_args(argv)

    data = json.loads(Path(args.input).read_text())
    findings = detect_and_load(data)

    # dedupe by (package, id)
    seen = set()
    unique: list[Finding] = []
    for f in findings:
        key = (f.package, f.id)
        if key in seen:
            continue
        seen.add(key)
        unique.append(f)

    reachable: set[str] = set()
    if args.reachable:
        for line in Path(args.reachable).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                reachable.add(line)

    for f in unique:
        f.score = score(f, reachable, args.prod_only)

    md, rows = group_and_render(unique)
    Path(args.out_md).write_text(md)
    Path(args.out_json).write_text(json.dumps({
        "findings": [asdict(f) for f in unique],
        "groups": rows,
    }, indent=2))
    print(f"Triaged {len(unique)} findings → {args.out_md}, {args.out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
