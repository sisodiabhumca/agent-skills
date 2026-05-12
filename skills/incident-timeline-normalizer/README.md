# incident-timeline-normalizer

Normalize mixed-format incident events into a single ordered timeline and compute basic phase durations.

## Run (sample)

```bash
python incident_timeline_normalizer.py \
  --events_json ../../samples/incident-timeline-normalizer/events.json \
  --out_json /tmp/incident_timeline.json
```

Output:
- `/tmp/incident_timeline.json`
