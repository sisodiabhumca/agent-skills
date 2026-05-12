# sql-anti-pattern-linter

Lint a SQL file for common anti-patterns.

## Run (sample)

```bash
python sql_anti_pattern_linter.py \
  --sql_file ../../samples/sql-anti-pattern-linter/query.sql \
  --out_json /tmp/sql_lint_findings.json
```

Output:
- `/tmp/sql_lint_findings.json`
