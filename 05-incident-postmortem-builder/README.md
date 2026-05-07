# incident-postmortem-builder

Build a blameless postmortem from a timeline + incident metadata.

## Run

```bash
python build.py \
  --incident-id INC-1234 --title "Checkout 5xx surge" --severity Sev2 \
  --started 2026-05-03T13:55:00Z \
  --detected 2026-05-03T14:02:00Z \
  --mitigated 2026-05-03T14:31:00Z \
  --resolved 2026-05-03T15:10:00Z \
  --timeline sample_timeline.csv \
  --impact-users 12000 --impact-revenue 4200
```

See [SKILL.md](./SKILL.md).
