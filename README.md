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
| [`ab-test-power-calculator`](./skills/ab-test-power-calculator) | Vendor-neutral skill to estimate experiment power, sample size, and runtime for product experiments. |
| [`access-review-coverage-auditor`](./skills/access-review-coverage-auditor) | Vendor-neutral skill to audit access review coverage and flag stale grants or missing attestations. |
| [`accessibility-alt-text-auditor`](./skills/accessibility-alt-text-auditor) | Vendor-neutral skill to audit image alt-text coverage and basic quality heuristics for accessibility. |
| [`ai-eval-regression-tester`](./skills/ai-eval-regression-tester) | Use to run a regression eval suite over an LLM application — fixed test cases with deterministic graders (exact match, JSON schema, regex, embedding similarity, LLM-as-judge). |
| [`ai-prompt-regression-tracker`](./skills/ai-prompt-regression-tracker) | Vendor-neutral skill to track prompt regressions across model versions with tagged eval outcomes. |
| [`api-changelog-impact-analyzer`](./skills/api-changelog-impact-analyzer) | Vendor-neutral skill for analyzing an API changelog and identifying likely breaking changes and downstream impacts. |
| [`api-changelog-summarizer`](./skills/api-changelog-summarizer) | Vendor-neutral skill to convert an API diff (before/after schemas or endpoints) into a structured changelog with breaking changes and migration guidance. |
| [`api-contract-diff`](./skills/api-contract-diff) | Vendor-neutral skill to compare two OpenAPI 3 specifications and produce a structured contract change report with breaking-change detection. |
| [`api-deprecation-impact-analyzer`](./skills/api-deprecation-impact-analyzer) | Vendor-neutral skill to analyze API deprecation impact on consumers and migration urgency. |
| [`api-error-budget-tracker`](./skills/api-error-budget-tracker) | Vendor-neutral skill to analyze API reliability metrics and summarize error budget burn with mitigation guidance. |
| [`api-rate-limit-impact-analyzer`](./skills/api-rate-limit-impact-analyzer) | Vendor-neutral skill to analyze rate-limit events and estimate customer-facing impact. |
| [`architecture-map-builder`](./skills/architecture-map-builder) | Use to build a service / component map from a GitHub or GitLab monorepo or set of repos. |
| [`backlog-prioritization-assistant`](./skills/backlog-prioritization-assistant) | Vendor-neutral skill to prioritize a backlog using configurable scoring (RICE/WSJF-style) and produce a ranked list with rationale. |
| [`billing-dispute-triage-assistant`](./skills/billing-dispute-triage-assistant) | Vendor-neutral skill to triage billing disputes and recommend resolution paths with evidence checks. |
| [`cache-invalidation-planner`](./skills/cache-invalidation-planner) | Vendor-neutral skill to plan cache invalidation strategies for high-risk data updates. |
| [`capacity-planning-signal-analyzer`](./skills/capacity-planning-signal-analyzer) | Vendor-neutral skill to synthesize utilization trends and forecast capacity risks for platform teams. |
| [`change-request-risk-scorer`](./skills/change-request-risk-scorer) | Vendor-neutral skill to score change requests using blast radius, rollback readiness, and dependency impact. |
| [`cloud-cost-tag-coverage-auditor`](./skills/cloud-cost-tag-coverage-auditor) | Audit cloud resource export data for missing or invalid cost allocation tags and output a vendor-neutral remediation plan. |
| [`competitive-win-loss-analyzer`](./skills/competitive-win-loss-analyzer) | Vendor-neutral skill to analyze win-loss notes and extract recurring competitive themes. |
| [`compliance-evidence-collector`](./skills/compliance-evidence-collector) | Vendor-neutral skill to map controls to evidence artifacts and flag audit readiness gaps. |
| [`config-drift-detector`](./skills/config-drift-detector) | Vendor-neutral skill to detect configuration drift across environments and suggest normalization actions. |
| [`cost-anomaly-explainer`](./skills/cost-anomaly-explainer) | Vendor-neutral skill to explain cloud cost anomalies by service, tag, and recent infrastructure changes. |
| [`crm-opportunity-summarizer`](./skills/crm-opportunity-summarizer) | Use when a sales rep or RevOps lead needs a concise opportunity summary from Salesforce or HubSpot — pulling stage, amount, contacts, recent activity, and risks, then producing a deal brief and recommended next-best-action. |
| [`csv-pii-redactor`](./skills/csv-pii-redactor) | Vendor-neutral skill to detect and redact common PII in CSV files and produce a redaction report. |
| [`csv-pii-scanner`](./skills/csv-pii-scanner) | Vendor-neutral skill to scan CSV exports for likely PII columns and risky values, producing a remediation-focused report. |
| [`customer-churn-risk-ranker`](./skills/customer-churn-risk-ranker) | Vendor-neutral skill to score customer churn risk from account signals and produce prioritized retention actions. |
| [`customer-health-score-explainer`](./skills/customer-health-score-explainer) | Vendor-neutral skill to explain customer health score movement with leading indicator breakdowns. |
| [`customer-interview-analyzer`](./skills/customer-interview-analyzer) | Use when a PM or UX researcher has interview transcripts (text/Notion/Drive) and needs themes, pain points, JTBD, and verbatim quotes synthesized into a research report. |
| [`customer-journey-gap-analyzer`](./skills/customer-journey-gap-analyzer) | Analyze a CSV of funnel stages and drop-offs to identify the biggest customer journey gaps and suggest prioritized experiments (vendor-neutral). |
| [`customer-reference-request-triager`](./skills/customer-reference-request-triager) | Vendor-neutral skill to triage reference requests by account fit, risk, and sales urgency. |
| [`data-contract-enforcer`](./skills/data-contract-enforcer) | Use to validate dbt models or warehouse tables against a data contract YAML. |
| [`data-contract-validator`](./skills/data-contract-validator) | Vendor-neutral skill to validate JSON records against a lightweight data contract (schema + rules) and produce a validation report. |
| [`data-pipeline-freshness-auditor`](./skills/data-pipeline-freshness-auditor) | Vendor-neutral skill to audit warehouse table freshness and rank downstream impact of delays. |
| [`data-quality-sla-monitor`](./skills/data-quality-sla-monitor) | Vendor-neutral skill to monitor data quality SLAs and produce remediation priorities for analytics teams. |
| [`data-retention-enforcement-planner`](./skills/data-retention-enforcement-planner) | Vendor-neutral skill to plan retention enforcement jobs with legal hold and deletion safeguards. |
| [`data-retention-policy-checker`](./skills/data-retention-policy-checker) | Vendor-neutral skill to check a data retention schedule for completeness and risk (coverage, deletion handling, legal holds) and produce a structured findings report. |
| [`dependency-vuln-triager`](./skills/dependency-vuln-triager) | Use to triage dependency vulnerability scanner output (npm audit, pip-audit, OSV, GitHub advisories) and produce a ranked, deduplicated action list. |
| [`deployment-freeze-advisor`](./skills/deployment-freeze-advisor) | Vendor-neutral skill to recommend deployment freeze windows from incident load and release risk signals. |
| [`docs-freshness-linter`](./skills/docs-freshness-linter) | Vendor-neutral skill to flag outdated documentation based on code churn and broken references. |
| [`docx-style-auditor`](./skills/docx-style-auditor) | Audits .docx documents for vendor-neutral style consistency issues (headings, spacing) and outputs an actionable report. |
| [`entitlement-drift-detector`](./skills/entitlement-drift-detector) | Vendor-neutral skill to detect entitlement mismatches between billing, product, and access systems. |
| [`error-budget-policy-linter`](./skills/error-budget-policy-linter) | Vendor-neutral skill to lint SLO and error budget policies for ambiguity and enforcement gaps. |
| [`etl-lineage-explainer`](./skills/etl-lineage-explainer) | Vendor-neutral skill for extracting and summarizing table-level lineage from SQL-based ETL jobs. |
| [`etl-retry-backoff-simulator`](./skills/etl-retry-backoff-simulator) | Simulate retry and exponential backoff strategies against a failure-rate model to estimate expected runtime and cost (vendor-neutral). |
| [`experiment-metric-audit`](./skills/experiment-metric-audit) | Vendor-neutral skill for auditing experiment metrics definitions for common analytics pitfalls and inconsistencies. |
| [`feature-adoption-funnel-builder`](./skills/feature-adoption-funnel-builder) | Builds vendor-neutral feature adoption funnels from event logs to quantify conversion, drop-off, and time-to-adopt. |
| [`feature-flag-cleanup-planner`](./skills/feature-flag-cleanup-planner) | Vendor-neutral skill to prioritize feature flags for cleanup using simple heuristics and produce a deprecation plan. |
| [`feature-flag-risk-assessor`](./skills/feature-flag-risk-assessor) | Vendor-neutral skill to assess risk in feature-flag configurations (stale flags, kill-switch coverage, conflicting rules) and produce actionable recommendations. |
| [`feature-flag-rollout-planner`](./skills/feature-flag-rollout-planner) | Vendor-neutral skill to generate a staged feature-flag rollout plan (phases, metrics, guardrails, rollback criteria) from feature context and risk inputs. |
| [`feature-request-deduplicator`](./skills/feature-request-deduplicator) | Vendor-neutral skill to cluster duplicate feature requests and summarize merged customer demand. |
| [`finops-chargeback-reporter`](./skills/finops-chargeback-reporter) | Vendor-neutral skill to produce chargeback reports with tag coverage and allocation confidence notes. |
| [`forecast-assumption-drift-checker`](./skills/forecast-assumption-drift-checker) | Vendor-neutral skill to compare forecast assumptions over time and flag high-impact drift. |
| [`growth-experiment-planner`](./skills/growth-experiment-planner) | Use when planning A/B tests in LaunchDarkly, Optimizely, or similar platforms. |
| [`http-api-smoke-tester`](./skills/http-api-smoke-tester) | Run a vendor-neutral HTTP API smoke test plan (requests + assertions) and emit a compact pass/fail report. |
| [`identity-provisioning-auditor`](./skills/identity-provisioning-auditor) | Vendor-neutral skill to audit identity provisioning workflows for timing, scope, and policy violations. |
| [`incident-comms-clarity-linter`](./skills/incident-comms-clarity-linter) | Vendor-neutral skill to lint incident communications for clarity, completeness, and stakeholder alignment. |
| [`incident-postmortem-builder`](./skills/incident-postmortem-builder) | Use after a production incident to build a blameless postmortem. |
| [`incident-postmortem-drafter`](./skills/incident-postmortem-drafter) | Vendor-neutral skill to draft a blameless incident postmortem from structured incident inputs (timeline, impact, contributing factors) and produce an actionable report. |
| [`incident-postmortem-qa-checklist`](./skills/incident-postmortem-qa-checklist) | Vendor-neutral skill to turn an incident timeline into a postmortem QA checklist and identify missing or weak evidence. |
| [`incident-severity-calibrator`](./skills/incident-severity-calibrator) | Vendor-neutral skill to calibrate incident severity from impact scope, duration, and customer tier. |
| [`incident-timeline-builder`](./skills/incident-timeline-builder) | Vendor-neutral skill to turn semi-structured incident logs into a normalized chronological timeline with clusters and gaps. |
| [`incident-timeline-normalizer`](./skills/incident-timeline-normalizer) | Vendor-neutral skill to normalize incident event logs into an ordered timeline and compute phase durations. |
| [`integration-test-gap-analyzer`](./skills/integration-test-gap-analyzer) | Vendor-neutral skill to find integration paths lacking automated tests after recent service changes. |
| [`inventory-staleness-auditor`](./skills/inventory-staleness-auditor) | Vendor-neutral skill to detect stale service inventory records and recommend ownership updates. |
| [`invoice-anomaly-detector`](./skills/invoice-anomaly-detector) | Vendor-neutral skill to flag billing anomalies in vendor invoices and produce reconciliation actions. |
| [`json-schema-drift-detector`](./skills/json-schema-drift-detector) | Detects vendor-neutral JSON Schema drift between two versions and produces an actionable change report. |
| [`kpi-anomaly-triage`](./skills/kpi-anomaly-triage) | Vendor-neutral skill to analyze KPI time-series data, detect anomalies, and generate a triage summary with likely drivers. |
| [`kpi-definition-consistency-checker`](./skills/kpi-definition-consistency-checker) | Vendor-neutral skill to check a KPI dictionary for conflicting definitions, grain mismatches, and missing ownership. |
| [`license-usage-optimizer`](./skills/license-usage-optimizer) | Vendor-neutral skill to find underused software licenses and recommend seat right-sizing actions. |
| [`log-redaction-auditor`](./skills/log-redaction-auditor) | Vendor-neutral skill to audit application logs for potential sensitive-data leakage and redaction coverage. |
| [`marketing-attribution-sanity-checker`](./skills/marketing-attribution-sanity-checker) | Vendor-neutral skill to audit marketing attribution models for double counting and channel bias. |
| [`meeting-action-item-extractor`](./skills/meeting-action-item-extractor) | Vendor-neutral skill to extract action items (task, owner, due date) from a meeting transcript into structured JSON. |
| [`meeting-action-items-extractor`](./skills/meeting-action-items-extractor) | Vendor-neutral skill to extract decisions, action items, and owners from meeting transcripts and output an actionable task list. |
| [`meeting-decision-log-extractor`](./skills/meeting-decision-log-extractor) | Vendor-neutral skill to extract decisions and action items from a meeting transcript and produce a decision log plus an action register. |
| [`meeting-notes-distiller`](./skills/meeting-notes-distiller) | Use when given a meeting transcript or raw notes to produce a structured summary — decisions made, action items (with owner + due date), risks/blockers, open questions, and a follow-up email draft. |
| [`mobile-crash-triage-assistant`](./skills/mobile-crash-triage-assistant) | Vendor-neutral skill to triage mobile crash clusters by release, device, and customer impact. |
| [`multi-tenant-noise-isolator`](./skills/multi-tenant-noise-isolator) | Vendor-neutral skill to isolate noisy-neighbor incidents across tenants using usage and latency signals. |
| [`nps-verbatim-theme-extractor`](./skills/nps-verbatim-theme-extractor) | Vendor-neutral skill to extract themes and sentiment drivers from NPS verbatim responses. |
| [`onboarding-dropoff-explainer`](./skills/onboarding-dropoff-explainer) | Vendor-neutral skill to analyze onboarding funnel dropoff and propose prioritized interventions. |
| [`oncall-handoff-summarizer`](./skills/oncall-handoff-summarizer) | Vendor-neutral skill to summarize on-call handoffs with open incidents, risks, and follow-up tasks. |
| [`oncall-runbook-executor`](./skills/oncall-runbook-executor) | Use during an incident or routine on-call task to execute a YAML-defined runbook step by step. |
| [`ops-rca-hypothesis-generator`](./skills/ops-rca-hypothesis-generator) | Generates vendor-neutral root-cause-analysis (RCA) hypotheses from incident symptoms and recent changes, producing a prioritized investigation plan. |
| [`pager-noise-reduction-advisor`](./skills/pager-noise-reduction-advisor) | Vendor-neutral skill to identify noisy alerts and propose paging policy improvements. |
| [`partner-api-health-monitor`](./skills/partner-api-health-monitor) | Vendor-neutral skill to monitor partner API health metrics and surface integration degradation risks. |
| [`pipeline-flake-detector`](./skills/pipeline-flake-detector) | Vendor-neutral skill to detect flaky CI jobs from historical run data and suggest stabilization actions. |
| [`policy-as-code-linter`](./skills/policy-as-code-linter) | Vendor-neutral skill for linting simple policy-as-code rules (YAML) for style, safety, and completeness. |
| [`pr-review-summarizer`](./skills/pr-review-summarizer) | Use when reviewing a code pull request or merge request. |
| [`pricing-experiment-readout-builder`](./skills/pricing-experiment-readout-builder) | Vendor-neutral skill to summarize pricing experiment outcomes with guardrails and rollout recommendations. |
| [`privacy-dsar-triage-assistant`](./skills/privacy-dsar-triage-assistant) | Vendor-neutral skill to triage data subject requests and map required systems and timelines. |
| [`privacy-policy-diff-summarizer`](./skills/privacy-policy-diff-summarizer) | Diff two privacy policy texts and produce a vendor-neutral summary of materially changed sections and risk flags. |
| [`procurement-rfp-comparator`](./skills/procurement-rfp-comparator) | Vendor-neutral skill to compare vendor RFP responses against weighted evaluation criteria. |
| [`product-analytics-investigator`](./skills/product-analytics-investigator) | Use when a PM, data PM, or analyst needs to investigate product metrics in Amplitude or Mixpanel — diagnosing drops in activation, retention, or funnel conversion, or attributing changes to releases, segments, or experiments. |
| [`product-feedback-router`](./skills/product-feedback-router) | Vendor-neutral skill to route product feedback to owners with priority and duplicate detection. |
| [`product-trial-conversion-explainer`](./skills/product-trial-conversion-explainer) | Vendor-neutral skill to explain trial conversion changes across cohorts, channels, and onboarding paths. |
| [`prompt-injection-risk-linter`](./skills/prompt-injection-risk-linter) | Vendor-neutral skill to lint agent prompts and untrusted retrieved content for prompt-injection risk patterns and missing safety boundaries. |
| [`pseudonymization-field-mapper`](./skills/pseudonymization-field-mapper) | Vendor-neutral skill to generate a consistent pseudonymization field map and implementation plan for datasets. |
| [`queue-backlog-prioritizer`](./skills/queue-backlog-prioritizer) | Vendor-neutral skill to prioritize engineering backlog items using impact, urgency, and dependency cost. |
| [`quota-forecast-builder`](./skills/quota-forecast-builder) | Vendor-neutral skill to forecast sales quota attainment from pipeline stage and historical conversion. |
| [`regulatory-guardrail-checker`](./skills/regulatory-guardrail-checker) | Use to screen a feature spec or product change for compliance risks across GDPR, CCPA, HIPAA, PCI-DSS, SOC2, and accessibility (WCAG 2.2). |
| [`release-notes-changelog-normalizer`](./skills/release-notes-changelog-normalizer) | Vendor-neutral skill to normalize raw release notes into Keep a Changelog-style entries with consistent headings. |
| [`release-notes-writer`](./skills/release-notes-writer) | Use to assemble user-facing release notes from a list of merged PRs (CSV/JSON) or by reading `git log` between two refs. |
| [`release-risk-checklist-builder`](./skills/release-risk-checklist-builder) | Vendor-neutral skill to generate a release risk checklist from scope, dependencies, and rollout constraints. |
| [`release-train-risk-ranker`](./skills/release-train-risk-ranker) | Vendor-neutral skill to rank release train candidates by dependency risk and rollback complexity. |
| [`renewal-churn-playbook-builder`](./skills/renewal-churn-playbook-builder) | Vendor-neutral skill to build renewal save playbooks from account health and usage decline signals. |
| [`roadmap-dependency-heatmap`](./skills/roadmap-dependency-heatmap) | Vendor-neutral skill to map roadmap dependencies and surface delivery risk concentrations. |
| [`rollback-readiness-checker`](./skills/rollback-readiness-checker) | Vendor-neutral skill to evaluate rollback readiness for releases using config, schema, and feature flags. |
| [`runbook-freshness-auditor`](./skills/runbook-freshness-auditor) | Vendor-neutral skill to identify stale runbooks and recommend updates based on recent incidents and ownership gaps. |
| [`saas-spend-optimizer`](./skills/saas-spend-optimizer) | Use to analyze SaaS billing/usage exports (Zuora, Stripe, vendor invoices) and surface optimization opportunities — unused seats, duplicate tools, over-provisioned tiers, autorenewals coming up, and ARR-at-risk. |
| [`sales-call-objection-clusterer`](./skills/sales-call-objection-clusterer) | Vendor-neutral skill to cluster sales call objections and extract response patterns for enablement. |
| [`sales-forecast-bias-checker`](./skills/sales-forecast-bias-checker) | Vendor-neutral skill to detect systematic forecast bias by rep, segment, and stage. |
| [`sbom-license-risk-checker`](./skills/sbom-license-risk-checker) | Vendor-neutral skill to check a CycloneDX SBOM for license policy compliance and emit a risk report. |
| [`schema-migration-risk-checker`](./skills/schema-migration-risk-checker) | Vendor-neutral skill to assess database schema migration risk from lock time, size, and dependency usage. |
| [`security-exception-expiry-tracker`](./skills/security-exception-expiry-tracker) | Vendor-neutral skill to track security exception expirations and generate remediation reminders. |
| [`shift-handover-checklist-builder`](./skills/shift-handover-checklist-builder) | Vendor-neutral skill to build shift handover checklists from open work, risks, and SLA exposure. |
| [`sql-anti-pattern-linter`](./skills/sql-anti-pattern-linter) | Vendor-neutral skill to lint SQL text for common anti-patterns and output actionable findings. |
| [`sqlite-schema-report`](./skills/sqlite-schema-report) | Vendor-neutral skill to summarize a SQLite database schema (tables, columns, indexes, foreign keys) and emit a portable report. |
| [`status-page-comms-drafter`](./skills/status-page-comms-drafter) | Vendor-neutral skill to draft status page updates from incident timelines and customer impact data. |
| [`subscription-downgrade-risk-scorer`](./skills/subscription-downgrade-risk-scorer) | Vendor-neutral skill to score downgrade risk from product usage and support interaction signals. |
| [`support-macro-gap-analyzer`](./skills/support-macro-gap-analyzer) | Vendor-neutral skill to find support ticket themes lacking macro coverage and draft macro candidates. |
| [`support-macro-personalizer`](./skills/support-macro-personalizer) | Vendor-neutral skill to render customer support macros with variables, validate placeholders, and output ready-to-send drafts. |
| [`support-sla-breach-detector`](./skills/support-sla-breach-detector) | Vendor-neutral skill for detecting support-ticket SLA breaches from exported ticket timelines. |
| [`synthetic-monitor-gap-finder`](./skills/synthetic-monitor-gap-finder) | Vendor-neutral skill to find critical user journeys missing synthetic monitoring coverage. |
| [`threat-model-gap-finder`](./skills/threat-model-gap-finder) | Vendor-neutral skill to compare threat models against architecture changes and surface missing controls. |
| [`usage-based-pricing-simulator`](./skills/usage-based-pricing-simulator) | Vendor-neutral skill to simulate usage-based pricing scenarios and margin outcomes. |
| [`utm-campaign-governor`](./skills/utm-campaign-governor) | Enforces vendor-neutral UTM naming conventions by validating marketing links and generating a normalized, policy-compliant output. |
| [`vendor-contract-renewal-planner`](./skills/vendor-contract-renewal-planner) | Vendor-neutral skill to prioritize upcoming vendor renewals from contract metadata and usage signals. |
| [`vendor-sla-breach-summarizer`](./skills/vendor-sla-breach-summarizer) | Vendor-neutral skill to summarize vendor SLA breaches and contract remedy options. |
| [`warehouse-query-cost-optimizer`](./skills/warehouse-query-cost-optimizer) | Vendor-neutral skill to identify expensive warehouse queries and recommend optimization actions. |
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

## Publish and index skills

The daily GitHub Action generates new skills, refreshes this README, validates the repository with `gh skill publish --dry-run`, commits the generated files, and publishes a GitHub release with `gh skill publish --tag ...`.

The public [skills.sh](https://www.skills.sh/sisodiabhumca/agent-skills) directory is updated by install telemetry from the `skills` CLI. GitHub Actions must not use `npx skills add` with CI environment variables set, because that tags requests with `ci=1` and skills.sh excludes them from the public collection. The workflow regenerates `skills.sh.json`, then calls `python scripts/index_skills_sh.py`, which performs a real install with CI markers unset, and verifies the skills.sh collection afterward.

If skills already exist in `main` but are missing from skills.sh, run the **Daily Skill Generator** workflow manually and leave `publish_existing` enabled. The workflow compares the repo against skills.sh and indexes only the missing skills.

## License

MIT — see [LICENSE](./LICENSE).
