# agent-skills

A growing collection of production-ready, **vendor-neutral Agent Skills** — usable by any AI agent or product. Each skill lives in `skills/<skill-name>/` with a `SKILL.md` (YAML frontmatter + instructions) and runnable Python reference code.

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

The table below is auto-generated from each skill's `SKILL.md` frontmatter. Run `python scripts/update_readme.py` after adding a skill to refresh it.

<!-- SKILLS-TABLE-START -->
| Skill | Description |
|---|---|
| [`ai-eval-regression-tester`](./skills/ai-eval-regression-tester) | Use to run a regression eval suite over an LLM application — fixed test cases with deterministic graders (exact match, JSON schema, regex, embedding similarity, LLM-as-judge). |
| [`architecture-map-builder`](./skills/architecture-map-builder) | Use to build a service / component map from a GitHub or GitLab monorepo or set of repos. |
| [`crm-opportunity-summarizer`](./skills/crm-opportunity-summarizer) | Use when a sales rep or RevOps lead needs a concise opportunity summary from Salesforce or HubSpot — pulling stage, amount, contacts, recent activity, and risks, then producing a deal brief and recommended next-best-action. |
| [`customer-interview-analyzer`](./skills/customer-interview-analyzer) | Use when a PM or UX researcher has interview transcripts (text/Notion/Drive) and needs themes, pain points, JTBD, and verbatim quotes synthesized into a research report. |
| [`data-contract-enforcer`](./skills/data-contract-enforcer) | Use to validate dbt models or warehouse tables against a data contract YAML. |
| [`dependency-vuln-triager`](./skills/dependency-vuln-triager) | Use to triage dependency vulnerability scanner output (npm audit, pip-audit, OSV, GitHub advisories) and produce a ranked, deduplicated action list. |
| [`growth-experiment-planner`](./skills/growth-experiment-planner) | Use when planning A/B tests in LaunchDarkly, Optimizely, or similar platforms. |
| [`incident-postmortem-builder`](./skills/incident-postmortem-builder) | Use after a production incident to build a blameless postmortem. |
| [`meeting-notes-distiller`](./skills/meeting-notes-distiller) | Use when given a meeting transcript or raw notes to produce a structured summary — decisions made, action items (with owner + due date), risks/blockers, open questions, and a follow-up email draft. |
| [`oncall-runbook-executor`](./skills/oncall-runbook-executor) | Use during an incident or routine on-call task to execute a YAML-defined runbook step by step. |
| [`pr-review-summarizer`](./skills/pr-review-summarizer) | Use when reviewing a code pull request or merge request. |
| [`product-analytics-investigator`](./skills/product-analytics-investigator) | Use when a PM, data PM, or analyst needs to investigate product metrics in Amplitude or Mixpanel — diagnosing drops in activation, retention, or funnel conversion, or attributing changes to releases, segments, or experiments. |
| [`regulatory-guardrail-checker`](./skills/regulatory-guardrail-checker) | Use to screen a feature spec or product change for compliance risks across GDPR, CCPA, HIPAA, PCI-DSS, SOC2, and accessibility (WCAG 2.2). |
| [`release-notes-writer`](./skills/release-notes-writer) | Use to assemble user-facing release notes from a list of merged PRs (CSV/JSON) or by reading `git log` between two refs. |
| [`saas-spend-optimizer`](./skills/saas-spend-optimizer) | Use to analyze SaaS billing/usage exports (Zuora, Stripe, vendor invoices) and surface optimization opportunities — unused seats, duplicate tools, over-provisioned tiers, autorenewals coming up, and ARR-at-risk. |
<!-- SKILLS-TABLE-END -->

## Skill format

Each skill folder contains only the spec, code, and (optionally) `requirements.txt` — sample/demo data lives in a parallel `samples/<skill-name>/` directory so security scanners (e.g. [SkillCheck by Repello](https://skills.repello.ai/)) only see code and instructions:

```
skills/<skill-name>/
├── SKILL.md          # YAML frontmatter (name, description) + instructions
├── README.md         # how to run the reference code
├── *.py              # working Python reference implementation
└── requirements.txt  # if any

samples/<skill-name>/
└── ...               # CSV/JSON/YAML/diff/etc. inputs used by the reference code
```

`SKILL.md` frontmatter:

```yaml
---
name: skill-name
description: When to use this skill (one or two sentences).
---
```

All skills are **vendor-neutral** — they call generic interfaces and work across any model provider, agent framework, or hosting platform.

## Run the test suite

```bash
./test_all_skills.sh
```

Tests every skill end-to-end against its sample input and asserts on output content. Exits 0 on full pass.

## License

MIT — see [LICENSE](./LICENSE).
