# feature-flag-risk-assessor

Analyzes a JSON export of feature flags and produces a risk report (stale flags, missing owners, conflicting rules, missing kill-switch patterns).

## Run

```bash
python /home/user/workspace/agent-skills/skills/feature-flag-risk-assessor/feature_flag_risk_assessor.py \
  --input ../../samples/feature-flag-risk-assessor/flags.json \
  --today 2026-06-09 \
  --output /tmp/flag_risk_report.json
```

```bash
cat /tmp/flag_risk_report.json
```
