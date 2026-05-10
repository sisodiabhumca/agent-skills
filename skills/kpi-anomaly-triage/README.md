# kpi-anomaly-triage

Detects anomalies in a KPI time series using a rolling z-score.

## Run on sample

```bash
python skills/kpi-anomaly-triage/kpi_anomaly_triage.py \
  --input ../../samples/kpi-anomaly-triage/kpi.csv \
  --out /tmp/kpi_anomaly_report.json \
  --window 7 \
  --z 2.5

cat /tmp/kpi_anomaly_report.json
```
