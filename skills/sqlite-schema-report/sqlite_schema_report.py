#!/usr/bin/env python3
"""Vendor-neutral SQLite schema report.

Reads a SQLite database in read-only mode and outputs a JSON schema summary.
Stdlib-only (sqlite3).
"""

import argparse
import json
import sqlite3
from typing import Any, Dict, List


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def list_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    return [r[0] for r in cur.fetchall()]


def table_columns(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    cur = conn.execute(f"PRAGMA table_info({quote_ident(table)})")
    cols = []
    for cid, name, ctype, notnull, dflt, pk in cur.fetchall():
        cols.append({"name": name, "type": ctype, "notnull": bool(notnull), "default": dflt, "pk": bool(pk)})
    return cols


def table_indexes(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    cur = conn.execute(f"PRAGMA index_list({quote_ident(table)})")
    out = []
    for seq, name, unique, origin, partial in cur.fetchall():
        cols = []
        cur2 = conn.execute(f"PRAGMA index_info({quote_ident(name)})")
        for _, _, colname in cur2.fetchall():
            cols.append(colname)
        out.append({"name": name, "unique": bool(unique), "origin": origin, "partial": bool(partial), "columns": cols})
    return out


def table_foreign_keys(conn: sqlite3.Connection, table: str) -> List[Dict[str, Any]]:
    cur = conn.execute(f"PRAGMA foreign_key_list({quote_ident(table)})")
    out = []
    for (id_, seq, tbl, from_, to, on_update, on_delete, match) in cur.fetchall():
        out.append(
            {
                "id": id_,
                "seq": seq,
                "table": tbl,
                "from": from_,
                "to": to,
                "on_update": on_update,
                "on_delete": on_delete,
                "match": match,
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--tables", default=None, help="Comma-separated list of tables (default: all)")
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        tables = list_tables(conn)
        if args.tables:
            wanted = [t.strip() for t in args.tables.split(",") if t.strip()]
            tables = [t for t in tables if t in wanted]

        report = {"database": args.db, "tables": []}
        for t in tables:
            report["tables"].append(
                {
                    "name": t,
                    "columns": table_columns(conn, t),
                    "indexes": table_indexes(conn, t),
                    "foreign_keys": table_foreign_keys(conn, t),
                }
            )

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, sort_keys=True, default=str)
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
