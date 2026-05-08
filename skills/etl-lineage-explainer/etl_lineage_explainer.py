#!/usr/bin/env python3
"""etl-lineage-explainer

Best-effort, vendor-neutral extraction of table-level lineage edges from SQL ETL scripts.

Design goals:
- stdlib-only
- directory or single-file input
- conservative regex-based parsing for common patterns

Not a full SQL parser.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
COMMENT_LINE_RE = re.compile(r"--.*?$", re.MULTILINE)

# Target patterns (keep simple; allow schema.table, db.schema.table)
INSERT_INTO_RE = re.compile(
    r"\binsert\s+into\s+(?P<target>[a-zA-Z0-9_\.\"\`\[\]]+)\b",
    re.IGNORECASE,
)
CREATE_AS_RE = re.compile(
    r"\bcreate\s+(?:or\s+replace\s+)?(?:table|view)\s+(?P<target>[a-zA-Z0-9_\.\"\`\[\]]+)\s+as\b",
    re.IGNORECASE,
)

# FROM/JOIN sources. Skip subqueries by ignoring "from (".
FROM_RE = re.compile(
    r"\bfrom\s+(?!\()(?P<source>[a-zA-Z0-9_\.\"\`\[\]]+)",
    re.IGNORECASE,
)
JOIN_RE = re.compile(
    r"\bjoin\s+(?!\()(?P<source>[a-zA-Z0-9_\.\"\`\[\]]+)",
    re.IGNORECASE,
)


def _strip_comments(sql: str) -> str:
    sql = COMMENT_BLOCK_RE.sub(" ", sql)
    sql = COMMENT_LINE_RE.sub(" ", sql)
    return sql


def _normalize_ident(ident: str) -> str:
    ident = ident.strip()
    # Remove common quoting wrappers; keep dots
    for ch in ['"', "`", "[", "]"]:
        ident = ident.replace(ch, "")
    # Collapse consecutive whitespace
    ident = re.sub(r"\s+", " ", ident)
    return ident


def _split_statements(sql: str) -> List[str]:
    # Very simple statement splitter on semicolons.
    # Keeps behavior stable for samples; not fully SQL-safe.
    parts = [p.strip() for p in sql.split(";")]
    return [p for p in parts if p]


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    file: str


def _extract_edges_from_statement(stmt: str, file_name: str) -> List[Edge]:
    targets: List[str] = []
    m = INSERT_INTO_RE.search(stmt)
    if m:
        targets.append(_normalize_ident(m.group("target")))
    m2 = CREATE_AS_RE.search(stmt)
    if m2:
        targets.append(_normalize_ident(m2.group("target")))

    if not targets:
        return []

    sources: Set[str] = set()
    for mm in FROM_RE.finditer(stmt):
        sources.add(_normalize_ident(mm.group("source")))
    for mm in JOIN_RE.finditer(stmt):
        sources.add(_normalize_ident(mm.group("source")))

    # Filter obvious SQL keywords mistakenly captured
    bad = {"select", "values"}
    sources = {s for s in sources if s.lower() not in bad}

    edges: List[Edge] = []
    for t in targets:
        for s in sorted(sources):
            edges.append(Edge(source=s, target=t, file=file_name))
    return edges


def _iter_sql_files(path: str) -> List[str]:
    if os.path.isdir(path):
        out: List[str] = []
        for root, _, files in os.walk(path):
            for fn in files:
                if fn.lower().endswith(".sql"):
                    out.append(os.path.join(root, fn))
        return sorted(out)
    return [path]


def build_lineage(input_path: str) -> Dict:
    edges: List[Edge] = []
    for fp in _iter_sql_files(input_path):
        with open(fp, "r", encoding="utf-8") as f:
            raw = f.read()
        sql = _strip_comments(raw)
        for stmt in _split_statements(sql):
            edges.extend(_extract_edges_from_statement(stmt, os.path.basename(fp)))

    # Consolidate
    targets: Dict[str, Dict[str, object]] = {}
    sources: Dict[str, Dict[str, object]] = {}
    for e in edges:
        targets.setdefault(e.target, {"sources": set(), "files": set()})
        targets[e.target]["sources"].add(e.source)  # type: ignore
        targets[e.target]["files"].add(e.file)  # type: ignore

        sources.setdefault(e.source, {"targets": set(), "files": set()})
        sources[e.source]["targets"].add(e.target)  # type: ignore
        sources[e.source]["files"].add(e.file)  # type: ignore

    def _freeze_sets(d: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
        out: Dict[str, Dict[str, object]] = {}
        for k, v in d.items():
            out[k] = {
                kk: sorted(list(vv)) if isinstance(vv, set) else vv
                for kk, vv in v.items()
            }
        return out

    return {
        "edges": [e.__dict__ for e in edges],
        "targets": _freeze_sets(targets),
        "sources": _freeze_sets(sources),
    }


def format_markdown(lineage: Dict) -> str:
    lines: List[str] = []
    edges = lineage.get("edges", [])
    lines.append(f"# ETL lineage summary\n\nExtracted {len(edges)} source→target edges.\n")

    lines.append("## Targets\n")
    for target in sorted(lineage.get("targets", {}).keys()):
        info = lineage["targets"][target]
        srcs = info.get("sources", [])
        files = info.get("files", [])
        lines.append(f"- **{target}**")
        if srcs:
            lines.append(f"  - Sources: {', '.join(srcs)}")
        if files:
            lines.append(f"  - Files: {', '.join(files)}")

    lines.append("\n## Sources\n")
    for source in sorted(lineage.get("sources", {}).keys()):
        info = lineage["sources"][source]
        tgts = info.get("targets", [])
        files = info.get("files", [])
        lines.append(f"- **{source}**")
        if tgts:
            lines.append(f"  - Downstream: {', '.join(tgts)}")
        if files:
            lines.append(f"  - Files: {', '.join(files)}")

    return "\n".join(lines).strip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Extract table-level lineage edges from SQL ETL scripts.")
    ap.add_argument("--input", required=True, help="SQL file or directory containing .sql files")
    ap.add_argument("--json-out", default=None, help="Optional path to write lineage JSON")
    args = ap.parse_args(argv)

    lineage = build_lineage(args.input)
    print(format_markdown(lineage))

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(lineage, f, indent=2, sort_keys=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
