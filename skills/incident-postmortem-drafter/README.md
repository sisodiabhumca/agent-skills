# incident-postmortem-drafter

Draft a blameless incident postmortem (Markdown) from structured incident inputs.

## Run

```bash
python postmortem_drafter.py \
  --input ../../samples/incident-postmortem-drafter/incident.json \
  --output /tmp/incident_postmortem.md
```

## Output
- A Markdown postmortem at the `--output` path.
