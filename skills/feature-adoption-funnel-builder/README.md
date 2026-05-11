# feature-adoption-funnel-builder

Vendor-neutral funnel builder for product event logs.

## Run

```bash
python feature_adoption_funnel_builder.py \
  --events ../../samples/feature-adoption-funnel-builder/events.csv \
  --steps "feature_viewed,feature_started,feature_completed" \
  --window-days 7 \
  --out /tmp/feature_funnel.json
```
