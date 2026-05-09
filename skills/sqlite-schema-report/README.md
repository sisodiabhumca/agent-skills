# sqlite-schema-report

Generates a JSON report describing a SQLite database schema (tables, columns, indexes, foreign keys).

## Run

```bash
python /home/user/workspace/agent-skills/skills/sqlite-schema-report/sqlite_schema_report.py \
  --db ../../samples/sqlite-schema-report/sample.db \
  --output /tmp/sqlite_schema_report.json
```

```bash
cat /tmp/sqlite_schema_report.json
```
