# support-macro-personalizer

Render customer-support macros with a context JSON and validate missing placeholders.

## Run (sample)

```bash
python support_macro_personalizer.py \
  --macros_json ../../samples/support-macro-personalizer/macros.json \
  --context_json ../../samples/support-macro-personalizer/context.json \
  --out_dir /tmp/support_drafts
```

Outputs:
- `/tmp/support_drafts/*.json`
