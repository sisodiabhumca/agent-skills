# meeting-action-items-extractor

Extracts action items and decisions from a plain-text transcript.

## Run on sample

```bash
python skills/meeting-action-items-extractor/meeting_action_items_extractor.py \
  --input ../../samples/meeting-action-items-extractor/transcript.txt \
  --out /tmp/meeting_actions.json

cat /tmp/meeting_actions.json
```
