# api-changelog-summarizer

Compare two OpenAPI JSON specs and output a markdown changelog.

## Run (sample)

```bash
python api_changelog_summarizer.py \
  --old_spec ../../samples/api-changelog-summarizer/openapi_old.json \
  --new_spec ../../samples/api-changelog-summarizer/openapi_new.json \
  --out_md /tmp/api_changelog.md
```

Output:
- `/tmp/api_changelog.md`
