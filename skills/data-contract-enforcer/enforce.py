"""Data Contract Enforcer.

Validates a table against a YAML contract. Defaults to DuckDB so the demo runs
without external dependencies; pass --dsn for SQLAlchemy connections to other
warehouses (snowflake, bigquery, postgres).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone


# Minimal YAML loader (subset) so the script stays dependency-free for the demo.
def load_yaml(path: str) -> dict:
    try:
        import yaml  # type: ignore
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        # Fallback: very small parser supporting the demo's contract shape.
        return _mini_yaml(open(path).read())


def _mini_yaml(text: str):
    """Parses a tiny subset of YAML for the demo contract."""
    import re
    root: dict = {}
    stack: list = [(0, root)]
    list_ctx = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        while stack and indent < stack[-1][0]:
            stack.pop()
        ctx = stack[-1][1]

        if line.startswith("- "):
            item_str = line[2:]
            if isinstance(ctx, list):
                if ":" in item_str:
                    k, v = item_str.split(":", 1)
                    obj = {k.strip(): _coerce(v.strip())}
                    ctx.append(obj)
                    stack.append((indent + 2, obj))
                else:
                    ctx.append(_coerce(item_str))
            continue

        m = re.match(r"^([\w_-]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        if val == "":
            # Could be dict or list child
            new: dict | list = {}
            ctx[key] = new
            stack.append((indent + 2, new))
            # peek next non-empty line for list detection
            new_list: list = []
            ctx[key] = new_list
            stack[-1] = (indent + 2, new_list)
            # We'll convert back to dict if first child is "key: value"
        else:
            ctx[key] = _coerce(val)
    return root


def _coerce(v: str):
    v = v.strip()
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v.strip('"').strip("'")


@dataclass
class Violation:
    level: str  # "ERROR" or "WARN"
    code: str
    message: str


def get_engine(dsn: str | None, duckdb_path: str | None):
    if dsn:
        from sqlalchemy import create_engine  # type: ignore
        return ("sa", create_engine(dsn))
    import duckdb  # type: ignore
    return ("duckdb", duckdb.connect(duckdb_path or ":memory:"))


def fetch_columns(kind, conn, table: str) -> list[dict]:
    if kind == "duckdb":
        rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
        return [{"name": r[1], "type": r[2].upper(), "nullable": not bool(r[3])} for r in rows]
    from sqlalchemy import inspect  # type: ignore
    insp = inspect(conn)
    schema = None
    name = table
    if "." in table:
        schema, name = table.split(".", 1)
    cols = insp.get_columns(name, schema=schema)
    return [{"name": c["name"], "type": str(c["type"]).upper(), "nullable": c.get("nullable", True)} for c in cols]


def scalar(kind, conn, sql: str):
    if kind == "duckdb":
        return conn.execute(sql).fetchone()[0]
    from sqlalchemy import text  # type: ignore
    with conn.connect() as c:
        return c.execute(text(sql)).scalar()


def enforce(contract: dict, kind, conn) -> list[Violation]:
    table = contract["table"]
    strict = bool(contract.get("strict"))
    violations: list[Violation] = []

    actual = fetch_columns(kind, conn, table)
    actual_by_name = {c["name"]: c for c in actual}

    for col in contract.get("columns", []) or []:
        n = col["name"]
        if n not in actual_by_name:
            violations.append(Violation("ERROR", "column_missing", f"Column `{n}` is missing"))
            continue
        a = actual_by_name[n]
        if col.get("type") and col["type"].upper() not in a["type"]:
            violations.append(Violation("ERROR", "type_mismatch", f"Column `{n}` expected {col['type']} got {a['type']}"))
        if col.get("nullable") is False and a["nullable"]:
            violations.append(Violation("ERROR", "nullable_mismatch", f"Column `{n}` is nullable in table but contract requires NOT NULL"))
        if col.get("unique"):
            dups = scalar(kind, conn, f"SELECT COUNT(*) - COUNT(DISTINCT {n}) FROM {table}")
            if dups and int(dups) > 0:
                violations.append(Violation("ERROR", "uniqueness", f"Column `{n}` has {dups} duplicate values"))
        if "min" in col:
            bad = scalar(kind, conn, f"SELECT COUNT(*) FROM {table} WHERE {n} < {col['min']}")
            if bad and int(bad) > 0:
                violations.append(Violation("ERROR", "min_violation", f"Column `{n}` has {bad} rows below min {col['min']}"))

    rc_spec = contract.get("row_count") or {}
    if rc_spec:
        n = scalar(kind, conn, f"SELECT COUNT(*) FROM {table}")
        if "min" in rc_spec and n < rc_spec["min"]:
            violations.append(Violation("ERROR", "row_count_min", f"Row count {n} below min {rc_spec['min']}"))
        if "max" in rc_spec and n > rc_spec["max"]:
            violations.append(Violation("ERROR", "row_count_max", f"Row count {n} above max {rc_spec['max']}"))

    fr = contract.get("freshness") or {}
    if fr.get("column") and fr.get("max_lag_minutes"):
        last = scalar(kind, conn, f"SELECT MAX({fr['column']}) FROM {table}")
        if last is None:
            violations.append(Violation("ERROR", "freshness_null", f"No rows / null max({fr['column']})"))
        else:
            if isinstance(last, str):
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            else:
                last_dt = last
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            lag_min = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
            if lag_min > fr["max_lag_minutes"]:
                level = "ERROR" if strict else "WARN"
                violations.append(Violation(level, "freshness_lag", f"Freshness lag {lag_min:.1f}min exceeds max {fr['max_lag_minutes']}min"))

    return violations


def render(table: str, violations: list[Violation]) -> str:
    if not violations:
        return f"# Data contract OK — `{table}`\n\nAll checks passed."
    lines = [f"# Data contract violations — `{table}`", ""]
    for v in violations:
        lines.append(f"- **{v.level}** [{v.code}] {v.message}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--dsn", default=None, help="SQLAlchemy DSN (e.g. snowflake://...) — defaults to DuckDB")
    ap.add_argument("--duckdb", default=None, help="Path to DuckDB file (defaults to in-memory + sample seed)")
    ap.add_argument("--seed", action="store_true", help="Seed an in-memory DuckDB with demo data")
    ap.add_argument("--json", action="store_true", help="Also emit JSON to stderr")
    args = ap.parse_args()

    contract = load_yaml(args.contract)
    kind, conn = get_engine(args.dsn, args.duckdb)

    if args.seed and kind == "duckdb":
        conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")
        conn.execute("""
            CREATE OR REPLACE TABLE analytics.fct_orders (
                order_id VARCHAR NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO analytics.fct_orders VALUES
              ('o1', 12.50, now()),
              ('o2', 88.00, now() - INTERVAL 30 MINUTE),
              ('o3', 4.25,  now() - INTERVAL 90 MINUTE)
        """)

    violations = enforce(contract, kind, conn)
    print(render(contract["table"], violations))
    if args.json:
        print(json.dumps([v.__dict__ for v in violations]), file=sys.stderr)
    errors = [v for v in violations if v.level == "ERROR"]
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
