# growth-experiment-planner

Size and brief A/B tests for LaunchDarkly / Optimizely.

## Run

```bash
python plan.py \
  --name "New onboarding v2" \
  --hypothesis "Shorter signup increases activation by 5%." \
  --metric-name "D1 activation rate" \
  --metric-type proportion --baseline 0.32 --mde 0.05 \
  --daily-users 12000 --variants 2 \
  --platform LaunchDarkly --owner "growth-pm@acme.com"
```

For a continuous metric:

```bash
python plan.py --metric-type mean --baseline 4.20 --stddev 2.10 --mde 0.03 --daily-users 8000
```

See [SKILL.md](./SKILL.md).
