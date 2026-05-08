# etl-lineage-explainer

Vendor-neutral skill to extract a table-level lineage approximation from SQL ETL scripts.

## Run on the bundled sample

```bash
python etl_lineage_explainer.py \
  --input ../../samples/etl-lineage-explainer/jobs.sql \
  --json-out /tmp/etl_lineage_explainer.json
```

The command prints a markdown summary to stdout and writes JSON to `/tmp/etl_lineage_explainer.json`.
