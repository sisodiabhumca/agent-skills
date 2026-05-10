# csv-pii-scanner

Heuristic scanner for likely PII in CSV files.

## Run on sample

```bash
python skills/csv-pii-scanner/csv_pii_scanner.py \
  --input ../../samples/csv-pii-scanner/customers.csv \
  --out /tmp/csv_pii_report.json

cat /tmp/csv_pii_report.json
```
