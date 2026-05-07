---
name: regulatory-guardrail-checker
description: Use to screen a feature spec or product change for compliance risks across GDPR, CCPA, HIPAA, PCI-DSS, SOC2, and accessibility (WCAG 2.2). Produces a risk register and required-controls checklist before launch.
---

# Regulatory Guardrail Checker

## When to invoke
- "Run compliance review on this PRD."
- "Does this feature touch PHI / PII?"
- "What guardrails do we need before launching in EU?"

## Inputs needed
1. **Spec text** — PRD or design doc (file or stdin).
2. **Regimes to check** — default: GDPR, CCPA, SOC2; opt-in: HIPAA, PCI, WCAG.
3. **Geographies / industries** (optional).

## Workflow
1. **Extract** signals from the spec: data types, third parties, user controls, retention, automation/AI use.
2. **Map** signals to regime obligations (lawful basis, DSR, BAAs, encryption, audit logging).
3. **Score risk** — High / Medium / Low per regime.
4. **Output** a risk register + required-controls checklist with owners.

## Output format
```
## Risk register
| Regime | Risk | Severity | Required control | Owner |
## Required controls checklist
- [ ] ...
## Open questions for legal/security
- ...
```

## Guardrails
- Never claim "compliant" — only "controls in place" or "controls missing".
- Surface **all** detected sensitive-data signals; do not hide on low confidence.
- Produce open questions for ambiguous areas.

## Reference code
`check.py` does pattern-based signal extraction and a rules-based mapping. Hooks for an LLM are provided but optional.
