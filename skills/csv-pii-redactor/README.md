# csv-pii-redactor

Detect likely PII in a CSV and redact flagged columns.

## Run (sample)

```bash
python csv_pii_redactor.py \
  --input_csv ../../samples/csv-pii-redactor/sample_customers.csv \
  --output_csv /tmp/sample_customers.redacted.csv \
  --report_json /tmp/sample_customers.redaction_report.json
```

Outputs:
- `/tmp/sample_customers.redacted.csv`
- `/tmp/sample_customers.redaction_report.json`
