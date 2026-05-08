# api-changelog-impact-analyzer

Vendor-neutral skill to analyze an API changelog and flag likely breaking changes.

## Run on the bundled sample

```bash
python api_changelog_impact_analyzer.py \
  --changelog ../../samples/api-changelog-impact-analyzer/changelog.md \
  --client-usage ../../samples/api-changelog-impact-analyzer/client_usage.json \
  --json-out /tmp/api_change_report.json
```
