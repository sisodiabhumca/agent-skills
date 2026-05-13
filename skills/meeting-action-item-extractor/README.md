# meeting-action-item-extractor

Extract action items (task, owner, due date) from a meeting transcript.

## Run

```bash
python extract_action_items.py \
  --transcript "../../samples/meeting-action-item-extractor/transcript.txt" \
  --participants "../../samples/meeting-action-item-extractor/participants.json" \
  --out "/tmp/action_items.json"
```
