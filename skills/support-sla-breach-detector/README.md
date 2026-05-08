# support-sla-breach-detector

Vendor-neutral skill to detect support SLA breaches from a ticket export CSV.

## Run on the bundled sample

```bash
python support_sla_breach_detector.py \
  --input ../../samples/support-sla-breach-detector/tickets.csv \
  --response-sla "P1=30,P2=120,P3=480" \
  --resolution-sla "P1=240,P2=1440,P3=4320" \
  --json-out /tmp/sla_breach_report.json
```
