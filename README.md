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
| [`accessibility-alt-text-auditor`](./skills/accessibility-alt-text-auditor) | Vendor-neutral skill to audit image alt-text coverage and basic quality heuristics for accessibility. |
| [`ai-eval-regression-tester`](./skills/ai-eval-regression-tester) | Use to run a regression eval suite over an LLM application — fixed test cases with deterministic graders (exact match, JSON schema, regex, embedding similarity, LLM-as-judge). |
| [`api-changelog-impact-analyzer`](./skills/api-changelog-impact-analyzer) | Vendor-neutral skill for analyzing an API changelog and identifying likely breaking changes and downstream impacts. |
| [`api-changelog-summarizer`](./skills/api-changelog-summarizer) | Vendor-neutral skill to compare two OpenAPI specs and summarize breaking and non-breaking API changes. |
| [`api-contract-diff`](./skills/api-contract-diff) | Vendor-neutral skill to compare two OpenAPI 3 specifications and produce a structured contract change report with breaking-change detection. |
| [`architecture-map-builder`](./skills/architecture-map-builder) | Use to build a service / component map from a GitHub or GitLab monorepo or set of repos. |
| [`backlog-prioritization-assistant`](./skills/backlog-prioritization-assistant) | Vendor-neutral skill to prioritize a backlog using configurable scoring (RICE/WSJF-style) and produce a ranked list with rationale. |
| [`cloud-cost-tag-coverage-auditor`](./skills/cloud-cost-tag-coverage-auditor) | Audit cloud resource export data for missing or invalid cost allocation tags and output a vendor-neutral remediation plan. |
| [`crm-opportunity-summarizer`](./skills/crm-opportunity-summarizer) | Use when a sales rep or RevOps lead needs a concise opportunity summary from Salesforce or HubSpot — pulling stage, amount, contacts, recent activity, and risks, then producing a deal brief and recommended next-best-action. |
| [`csv-pii-redactor`](./skills/csv-pii-redactor) | Vendor-neutral skill to detect and redact common PII in CSV files and produce a redaction report. |
| [`csv-pii-scanner`](./skills/csv-pii-scanner) | Vendor-neutral skill to scan CSV exports for likely PII columns and risky values, producing a remediation-focused report. |
| [`customer-interview-analyzer`](./skills/customer-interview-analyzer) | Use when a PM or UX researcher has interview transcripts (text/Notion/Drive) and needs themes, pain points, JTBD, and verbatim quotes synthesized into a research report. |
| [`customer-journey-gap-analyzer`](./skills/customer-journey-gap-analyzer) | Analyze a CSV of funnel stages and drop-offs to identify the biggest customer journey gaps and suggest prioritized experiments (vendor-neutral). |
| [`data-contract-enforcer`](./skills/data-contract-enforcer) | Use to validate dbt models or warehouse tables against a data contract YAML. |
| [`data-contract-validator`](./skills/data-contract-validator) | Vendor-neutral skill to validate JSON records against a lightweight data contract (schema + rules) and produce a validation report. |
| [`dependency-vuln-triager`](./skills/dependency-vuln-triager) | Use to triage dependency vulnerability scanner output (npm audit, pip-audit, OSV, GitHub advisories) and produce a ranked, deduplicated action list. |
| [`docx-style-auditor`](./skills/docx-style-auditor) | Audits .docx documents for vendor-neutral style consistency issues (headings, spacing) and outputs an actionable report. |
| [`etl-lineage-explainer`](./skills/etl-lineage-explainer) | Vendor-neutral skill for extracting and summarizing table-level lineage from SQL-based ETL jobs. |
| [`etl-retry-backoff-simulator`](./skills/etl-retry-backoff-simulator) | Simulate retry and exponential backoff strategies against a failure-rate model to estimate expected runtime and cost (vendor-neutral). |
| [`experiment-metric-audit`](./skills/experiment-metric-audit) | Vendor-neutral skill for auditing experiment metrics definitions for common analytics pitfalls and inconsistencies. |
| [`feature-adoption-funnel-builder`](./skills/feature-adoption-funnel-builder) | Builds vendor-neutral feature adoption funnels from event logs to quantify conversion, drop-off, and time-to-adopt. |
| [`feature-flag-cleanup-planner`](./skills/feature-flag-cleanup-planner) | Vendor-neutral skill to prioritize feature flags for cleanup using simple heuristics and produce a deprecation plan. |
| [`feature-flag-risk-assessor`](./skills/feature-flag-risk-assessor) | Vendor-neutral skill to assess risk in feature-flag configurations (stale flags, kill-switch coverage, conflicting rules) and produce actionable recommendations. |
| [`growth-experiment-planner`](./skills/growth-experiment-planner) | Use when planning A/B tests in LaunchDarkly, Optimizely, or similar platforms. |
| [`http-api-smoke-tester`](./skills/http-api-smoke-tester) | Run a vendor-neutral HTTP API smoke test plan (requests + assertions) and emit a compact pass/fail report. |
| [`incident-postmortem-builder`](./skills/incident-postmortem-builder) | Use after a production incident to build a blameless postmortem. |
| [`incident-postmortem-qa-checklist`](./skills/incident-postmortem-qa-checklist) | Vendor-neutral skill to turn an incident timeline into a postmortem QA checklist and identify missing or weak evidence. |
| [`incident-timeline-builder`](./skills/incident-timeline-builder) | Vendor-neutral skill to turn semi-structured incident logs into a normalized chronological timeline with clusters and gaps. |
| [`incident-timeline-normalizer`](./skills/incident-timeline-normalizer) | Vendor-neutral skill to normalize incident event logs into an ordered timeline and compute phase durations. |
| [`json-schema-drift-detector`](./skills/json-schema-drift-detector) | Detects vendor-neutral JSON Schema drift between two versions and produces an actionable change report. |
| [`kpi-anomaly-triage`](./skills/kpi-anomaly-triage) | Vendor-neutral skill to analyze KPI time-series data, detect anomalies, and generate a triage summary with likely drivers. |
| [`kpi-definition-consistency-checker`](./skills/kpi-definition-consistency-checker) | Vendor-neutral skill to check a KPI dictionary for conflicting definitions, grain mismatches, and missing ownership. |
| [`log-redaction-auditor`](./skills/log-redaction-auditor) | Vendor-neutral skill to audit application logs for potential sensitive-data leakage and redaction coverage. |
| [`meeting-action-item-extractor`](./skills/meeting-action-item-extractor) | Vendor-neutral skill to extract action items (task, owner, due date) from a meeting transcript into structured JSON. |
| [`meeting-action-items-extractor`](./skills/meeting-action-items-extractor) | Vendor-neutral skill to extract decisions, action items, and owners from meeting transcripts and output an actionable task list. |
| [`meeting-notes-distiller`](./skills/meeting-notes-distiller) | Use when given a meeting transcript or raw notes to produce a structured summary — decisions made, action items (with owner + due date), risks/blockers, open questions, and a follow-up email draft. |
| [`oncall-runbook-executor`](./skills/oncall-runbook-executor) | Use during an incident or routine on-call task to execute a YAML-defined runbook step by step. |
| [`ops-rca-hypothesis-generator`](./skills/ops-rca-hypothesis-generator) | Generates vendor-neutral root-cause-analysis (RCA) hypotheses from incident symptoms and recent changes, producing a prioritized investigation plan. |
| [`policy-as-code-linter`](./skills/policy-as-code-linter) | Vendor-neutral skill for linting simple policy-as-code rules (YAML) for style, safety, and completeness. |
| [`pr-review-summarizer`](./skills/pr-review-summarizer) | Use when reviewing a code pull request or merge request. |
| [`privacy-policy-diff-summarizer`](./skills/privacy-policy-diff-summarizer) | Diff two privacy policy texts and produce a vendor-neutral summary of materially changed sections and risk flags. |
| [`product-analytics-investigator`](./skills/product-analytics-investigator) | Use when a PM, data PM, or analyst needs to investigate product metrics in Amplitude or Mixpanel — diagnosing drops in activation, retention, or funnel conversion, or attributing changes to releases, segments, or experiments. |
| [`prompt-injection-risk-linter`](./skills/prompt-injection-risk-linter) | Vendor-neutral skill to lint agent prompts and untrusted retrieved content for prompt-injection risk patterns and missing safety boundaries. |
| [`pseudonymization-field-mapper`](./skills/pseudonymization-field-mapper) | Vendor-neutral skill to generate a consistent pseudonymization field map and implementation plan for datasets. |
| [`regulatory-guardrail-checker`](./skills/regulatory-guardrail-checker) | Use to screen a feature spec or product change for compliance risks across GDPR, CCPA, HIPAA, PCI-DSS, SOC2, and accessibility (WCAG 2.2). |
| [`release-notes-changelog-normalizer`](./skills/release-notes-changelog-normalizer) | Vendor-neutral skill to normalize raw release notes into Keep a Changelog-style entries with consistent headings. |
| [`release-notes-writer`](./skills/release-notes-writer) | Use to assemble user-facing release notes from a list of merged PRs (CSV/JSON) or by reading `git log` between two refs. |
| [`saas-spend-optimizer`](./skills/saas-spend-optimizer) | Use to analyze SaaS billing/usage exports (Zuora, Stripe, vendor invoices) and surface optimization opportunities — unused seats, duplicate tools, over-provisioned tiers, autorenewals coming up, and ARR-at-risk. |
| [`sbom-license-risk-checker`](./skills/sbom-license-risk-checker) | Vendor-neutral skill to check a CycloneDX SBOM for license policy compliance and emit a risk report. |
| [`sql-anti-pattern-linter`](./skills/sql-anti-pattern-linter) | Vendor-neutral skill to lint SQL text for common anti-patterns and output actionable findings. |
| [`sqlite-schema-report`](./skills/sqlite-schema-report) | Vendor-neutral skill to summarize a SQLite database schema (tables, columns, indexes, foreign keys) and emit a portable report. |
| [`support-macro-personalizer`](./skills/support-macro-personalizer) | Vendor-neutral skill to render customer support macros with variables, validate placeholders, and output ready-to-send drafts. |
| [`support-sla-breach-detector`](./skills/support-sla-breach-detector) | Vendor-neutral skill for detecting support-ticket SLA breaches from exported ticket timelines. |
| [`utm-campaign-governor`](./skills/utm-campaign-governor) | Enforces vendor-neutral UTM naming conventions by validating marketing links and generating a normalized, policy-compliant output. |
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
