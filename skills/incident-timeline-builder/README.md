# incident-timeline-builder

Builds a normalized incident timeline from timestamped lines.

## Run on sample

```bash
python skills/incident-timeline-builder/incident_timeline_builder.py \
  --input ../../samples/incident-timeline-builder/incident_log.txt \
  --out /tmp/incident_timeline.json \
  --gap-minutes 15

cat /tmp/incident_timeline.json
```
