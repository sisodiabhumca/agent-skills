# agent-skills

A collection of 10 production-ready Agent Skills, each in `skills/{skill-name}/` with a `SKILL.md` and runnable Python reference code.

Compatible with the [skills.sh](https://skills.sh) directory layout.

## Install (whole collection)

```bash
npx skills add sisodiabhumca/agent-skills
```

## Install one skill

```bash
npx skills add https://github.com/sisodiabhumca/agent-skills --skill product-analytics-investigator
```

## Skills

| Skill | Domain | Persona |
|---|---|---|
| [product-analytics-investigator](./skills/product-analytics-investigator) | Amplitude / Mixpanel | PM, data PM, analyst |
| [growth-experiment-planner](./skills/growth-experiment-planner) | LaunchDarkly / Optimizely | PM, growth, marketing |
| [crm-opportunity-summarizer](./skills/crm-opportunity-summarizer) | Salesforce / HubSpot | Sales, RevOps |
| [customer-interview-analyzer](./skills/customer-interview-analyzer) | Research / Notion / Drive | PM, UX researcher |
| [incident-postmortem-builder](./skills/incident-postmortem-builder) | SRE / observability | SRE, DevOps |
| [data-contract-enforcer](./skills/data-contract-enforcer) | dbt / warehouse | Analytics eng, data eng |
| [saas-spend-optimizer](./skills/saas-spend-optimizer) | Billing / Zuora | Finance, RevOps |
| [regulatory-guardrail-checker](./skills/regulatory-guardrail-checker) | Compliance | PM, legal, security |
| [architecture-map-builder](./skills/architecture-map-builder) | GitHub / GitLab | Staff eng, platform |
| [ai-eval-regression-tester](./skills/ai-eval-regression-tester) | LLM apps | AI eng, MLE |

## Skill format

Each skill follows the standard layout:

```
skills/<skill-name>/
├── SKILL.md          # YAML frontmatter (name, description) + instructions
├── README.md         # how to run the reference code
├── *.py              # working Python reference implementation
├── requirements.txt  # if any
└── sample_*          # sample inputs for the demo
```

`SKILL.md` frontmatter:

```yaml
---
name: skill-name
description: When to use this skill (one or two sentences).
---
```

## Run the test suite

```bash
./test_all_skills.sh
```

Tests every skill end-to-end against its sample input and asserts on output content. Exits 0 on full pass.

## License

MIT — see [LICENSE](./LICENSE).
