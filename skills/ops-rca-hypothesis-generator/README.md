# ops-rca-hypothesis-generator

Vendor-neutral helper to generate testable RCA hypotheses from incident symptoms and recent changes.

## Run

```bash
python ops_rca_hypothesis_generator.py \
  --incident ../../samples/ops-rca-hypothesis-generator/incident.json \
  --changes ../../samples/ops-rca-hypothesis-generator/changes.json \
  --out /tmp/rca_hypotheses.json
```
