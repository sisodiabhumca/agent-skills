"""Architecture Map Builder.

Walks a directory of repos / a monorepo, detects services, infers internal
dependencies, and emits services.yml + architecture.mmd + report.md.

Usage:
  python map.py --path ./repos --out ./out
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path


SERVICE_MARKERS = ["Dockerfile", "package.json", "pyproject.toml", "go.mod", "Cargo.toml", "pom.xml", "build.gradle"]
SOURCE_EXT = {".py", ".js", ".ts", ".tsx", ".go", ".rb", ".java", ".kt", ".rs"}


@dataclass
class Service:
    name: str
    path: str
    language: str = "unknown"
    framework: str = ""
    owners: list[str] = field(default_factory=list)
    deps: set[str] = field(default_factory=set)


def detect_language(svc_path: Path) -> tuple[str, str]:
    if (svc_path / "package.json").exists():
        try:
            j = json.loads((svc_path / "package.json").read_text())
            for fw in ("next", "express", "fastify", "nestjs"):
                if fw in (j.get("dependencies", {}) | j.get("devDependencies", {})):
                    return ("typescript" if (svc_path / "tsconfig.json").exists() else "javascript", fw)
            return ("typescript" if (svc_path / "tsconfig.json").exists() else "javascript", "")
        except Exception:
            return ("javascript", "")
    if (svc_path / "pyproject.toml").exists() or (svc_path / "requirements.txt").exists():
        text = ""
        for f in ("pyproject.toml", "requirements.txt"):
            p = svc_path / f
            if p.exists():
                text += p.read_text(errors="ignore")
        for fw in ("fastapi", "django", "flask"):
            if fw in text.lower():
                return ("python", fw)
        return ("python", "")
    if (svc_path / "go.mod").exists():
        return ("go", "")
    if (svc_path / "Cargo.toml").exists():
        return ("rust", "")
    if (svc_path / "pom.xml").exists() or (svc_path / "build.gradle").exists():
        return ("java", "")
    return ("unknown", "")


def find_codeowners(repo_root: Path) -> dict[str, list[str]]:
    """Returns {path_pattern: [owners]} from CODEOWNERS."""
    out: dict[str, list[str]] = {}
    for cand in (repo_root / "CODEOWNERS", repo_root / ".github" / "CODEOWNERS", repo_root / "docs" / "CODEOWNERS"):
        if cand.exists():
            for line in cand.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    out[parts[0]] = parts[1:]
    return out


def discover_services(root: Path) -> list[Service]:
    seen: dict[str, Service] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip vendored / heavy folders
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".git", "vendor", "dist", "build", ".venv"}]
        if any(m in filenames for m in SERVICE_MARKERS):
            p = Path(dirpath)
            name = p.name if p.name else "root"
            # avoid double-detecting at parent + child if both have markers
            key = str(p.resolve())
            if key in seen:
                continue
            lang, fw = detect_language(p)
            seen[key] = Service(name=name, path=str(p), language=lang, framework=fw)
    return list(seen.values())


def assign_owners(services: list[Service], root: Path) -> None:
    co = find_codeowners(root)
    for s in services:
        rel = "/" + str(Path(s.path).resolve().relative_to(root.resolve())).replace(os.sep, "/")
        for pat, owners in co.items():
            if pat == "*" or rel.startswith(pat.rstrip("/*")):
                s.owners = owners


def detect_deps(services: list[Service]) -> None:
    names = {s.name for s in services}
    name_patterns = {n: re.compile(rf"\b{re.escape(n)}\b") for n in names}
    host_patterns = {n: re.compile(rf"https?://[^\s\"']*\b{re.escape(n)}\b[^\s\"']*") for n in names}

    for s in services:
        for path, _, files in os.walk(s.path):
            if any(skip in path for skip in ("node_modules", ".git", "vendor", "dist", "build")):
                continue
            for f in files:
                if Path(f).suffix not in SOURCE_EXT:
                    continue
                fp = Path(path) / f
                try:
                    text = fp.read_text(errors="ignore")
                except Exception:
                    continue
                for other_name, pat in host_patterns.items():
                    if other_name == s.name:
                        continue
                    if pat.search(text):
                        s.deps.add(other_name)
                # Cheap import heuristic for in-repo modules
                for other_name, pat in name_patterns.items():
                    if other_name == s.name:
                        continue
                    if re.search(rf"(import|from|require)\b[^\n]{{0,80}}\b{re.escape(other_name)}\b", text):
                        s.deps.add(other_name)


def find_cycles(services: list[Service]) -> list[list[str]]:
    graph = {s.name: set(s.deps) for s in services}
    cycles: list[list[str]] = []
    visiting, visited = set(), set()

    def dfs(node, stack):
        if node in stack:
            cycles.append(stack[stack.index(node):] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        for nxt in graph.get(node, ()):
            dfs(nxt, stack + [node])
        visiting.discard(node)
        visited.add(node)

    for s in services:
        dfs(s.name, [])
    # dedupe
    uniq = []
    seen = set()
    for c in cycles:
        key = tuple(sorted(c))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def emit_mermaid(services: list[Service]) -> str:
    out = ["graph LR"]
    for s in services:
        out.append(f'  {sanitize(s.name)}["{s.name}<br/><i>{s.language}</i>"]')
    for s in services:
        for d in sorted(s.deps):
            out.append(f"  {sanitize(s.name)} --> {sanitize(d)}")
    return "\n".join(out)


def sanitize(n: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", n)


def emit_yaml(services: list[Service]) -> str:
    lines = ["services:"]
    for s in services:
        lines += [
            f"  - name: {s.name}",
            f"    path: {s.path}",
            f"    language: {s.language}",
            f"    framework: {s.framework}",
            f"    owners: [{', '.join(s.owners)}]",
            f"    deps: [{', '.join(sorted(s.deps))}]",
        ]
    return "\n".join(lines)


def emit_report(services: list[Service], cycles: list[list[str]]) -> str:
    no_owner = [s.name for s in services if not s.owners]
    lines = [
        f"# Architecture Map",
        "",
        f"- **Services discovered:** {len(services)}",
        f"- **Languages:** {', '.join(sorted({s.language for s in services}))}",
        "",
        "## Risks",
    ]
    if no_owner:
        lines.append(f"- **Missing owners** ({len(no_owner)}): {', '.join(no_owner)}")
    else:
        lines.append("- All services have owners ✅")
    if cycles:
        lines.append(f"- **Dependency cycles detected**: {len(cycles)}")
        for c in cycles:
            lines.append(f"  - {' → '.join(c)}")
    else:
        lines.append("- No cycles detected ✅")
    lines += ["", "## Services"]
    for s in sorted(services, key=lambda s: s.name):
        deps = ", ".join(sorted(s.deps)) or "—"
        owners = ", ".join(s.owners) or "—"
        lines.append(f"- **{s.name}** ({s.language}{', ' + s.framework if s.framework else ''}) — owners: {owners} — deps: {deps}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--path", required=True)
    ap.add_argument("--out", default="./out")
    args = ap.parse_args()

    root = Path(args.path).resolve()
    services = discover_services(root)
    assign_owners(services, root)
    detect_deps(services)
    cycles = find_cycles(services)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "services.yml").write_text(emit_yaml(services))
    (out / "architecture.mmd").write_text(emit_mermaid(services))
    (out / "report.md").write_text(emit_report(services, cycles))

    print(f"Wrote {out}/services.yml, architecture.mmd, report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
