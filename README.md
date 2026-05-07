# Agent Skills

A monorepo of 10 production-ready Agent Skills for Perplexity Computer (and compatible agent runtimes). Each skill ships with:

- `SKILL.md` — skill definition with YAML frontmatter, instructions, and usage notes
- Working Python reference code that implements the core workflow
- A focused `README.md` and tests/sample data where applicable

## Skills

| # | Skill | Domain | Persona |
|---|-------|--------|---------|
| 1 | [product-analytics-investigator](./01-product-analytics-investigator) | Amplitude / Mixpanel | PM, data PM, analyst |
| 2 | [growth-experiment-planner](./02-growth-experiment-planner) | LaunchDarkly / Optimizely | PM, growth, marketing |
| 3 | [crm-opportunity-summarizer](./03-crm-opportunity-summarizer) | Salesforce / HubSpot | Sales, RevOps |
| 4 | [customer-interview-analyzer](./04-customer-interview-analyzer) | Research / Notion / Drive | PM, UX researcher |
| 5 | [incident-postmortem-builder](./05-incident-postmortem-builder) | SRE / observability | SRE, DevOps |
| 6 | [data-contract-enforcer](./06-data-contract-enforcer) | dbt / warehouse | Analytics eng, data eng |
| 7 | [saas-spend-optimizer](./07-saas-spend-optimizer) | Billing / Zuora | Finance, RevOps |
| 8 | [regulatory-guardrail-checker](./08-regulatory-guardrail-checker) | Compliance | PM, legal, security |
| 9 | [architecture-map-builder](./09-architecture-map-builder) | GitHub / GitLab | Staff eng, platform |
| 10 | [ai-eval-regression-tester](./10-ai-eval-regression-tester) | LLM apps | AI eng, MLE |

## Skill format

Each `SKILL.md` follows the Agent Skill convention:

```yaml
---
name: skill-name
description: When to use this skill (one or two sentences).
---
# Skill instructions in Markdown
```

Skills are designed to be loaded by the agent runtime; reference scripts are runnable standalone (`python script.py --help`).

## Quickstart

```bash
git clone https://github.com/sisodiabhumca/agent-skills.git
cd agent-skills/01-product-analytics-investigator
pip install -r requirements.txt
python investigate.py --help
```

## License

MIT — see [LICENSE](./LICENSE).
