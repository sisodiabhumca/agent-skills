---
name: ops-rca-hypothesis-generator
description: Generates vendor-neutral root-cause-analysis (RCA) hypotheses from incident symptoms and recent changes, producing a prioritized investigation plan.
---

## When to invoke
- After an outage/incident when you have symptoms and a change log but no confirmed cause.
- You want a structured, testable list of hypotheses with next steps.

## Inputs needed
- `--incident`: JSON describing impact window, symptoms, and affected components.
- `--changes`: JSON list of recent changes (deploys, config, infra).
- Optional: `--out`: Path to write hypotheses JSON.

## Workflow
1. Load incident and change entries.
2. Extract keywords from symptoms/components.
3. Score each change by time proximity and keyword overlap.
4. Generate hypotheses:
   - “Change X caused symptom Y via mechanism Z”.
5. For each hypothesis, produce:
   - quick checks (logs/metrics/flags)
   - deeper validation
   - rollback/mitigation options
6. Output top hypotheses sorted by score.

## Output format
JSON with:
- `incident_summary`
- `hypotheses`: list with `rank`, `score`, `hypothesis`, `evidence`, `next_steps`

## Guardrails
- Do not claim certainty; hypotheses must be framed as testable.
- Avoid blaming individuals; focus on systems.
- Keep guidance vendor-neutral (no tool-specific commands).

## Reference code
Use `ops_rca_hypothesis_generator.py`.
