# json-schema-drift-detector

Vendor-neutral tool to detect drift between two JSON Schema documents.

## Run

```bash
python json_schema_drift_detector.py \
  --old ../../samples/json-schema-drift-detector/old_schema.json \
  --new ../../samples/json-schema-drift-detector/new_schema.json \
  --out /tmp/json_schema_drift_report.json
```

The command prints a short summary and writes the full JSON report to `/tmp/json_schema_drift_report.json`.
