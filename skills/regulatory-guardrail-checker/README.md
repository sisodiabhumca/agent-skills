# regulatory-guardrail-checker

Pre-launch compliance review for PRDs / design docs. Produces a risk register and required-controls checklist.

## Run

```bash
python check.py --spec ../../samples/regulatory-guardrail-checker/sample_spec.md --regimes gdpr,ccpa,soc2,wcag
```

See [SKILL.md](./SKILL.md).

## Sample data

Sample inputs for this skill live in `../../samples/regulatory-guardrail-checker/` (kept outside the skill folder so security scanners don't need to handle non-code data).
