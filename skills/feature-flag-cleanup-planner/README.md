# feature-flag-cleanup-planner

Analyze a feature-flag inventory and produce a vendor-neutral cleanup plan.

## Run

```bash
python plan_cleanup.py \
  --flags "../../samples/feature-flag-cleanup-planner/flags.json" \
  --out "/tmp/flag_cleanup_plan.json"
```
