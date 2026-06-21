"""Create 5 new skill scaffolds per UTC day from a rotating template catalog.

Skill directories use stable slugs only (for example `sales-call-objection-clusterer`).
Each run picks five templates that are not already present in `skills/`, starting
from a day-rotated offset in the catalog.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
SAMPLES_DIR = ROOT / "samples"


@dataclass(frozen=True)
class SkillTemplate:
    slug: str
    title: str
    description: str


# Candidate skills for the daily generator. Existing repo skills are skipped automatically.
TEMPLATES = [
    SkillTemplate(
        slug="vendor-contract-renewal-planner",
        title="Vendor Contract Renewal Planner",
        description="Vendor-neutral skill to prioritize upcoming vendor renewals from contract metadata and usage signals.",
    ),
    SkillTemplate(
        slug="capacity-planning-signal-analyzer",
        title="Capacity Planning Signal Analyzer",
        description="Vendor-neutral skill to synthesize utilization trends and forecast capacity risks for platform teams.",
    ),
    SkillTemplate(
        slug="change-request-risk-scorer",
        title="Change Request Risk Scorer",
        description="Vendor-neutral skill to score change requests using blast radius, rollback readiness, and dependency impact.",
    ),
    SkillTemplate(
        slug="data-quality-sla-monitor",
        title="Data Quality SLA Monitor",
        description="Vendor-neutral skill to monitor data quality SLAs and produce remediation priorities for analytics teams.",
    ),
    SkillTemplate(
        slug="pricing-experiment-readout-builder",
        title="Pricing Experiment Readout Builder",
        description="Vendor-neutral skill to summarize pricing experiment outcomes with guardrails and rollout recommendations.",
    ),
    SkillTemplate(
        slug="support-escalation-router",
        title="Support Escalation Router",
        description="Vendor-neutral skill to route support escalations based on severity, customer tier, and SLA exposure.",
    ),
    SkillTemplate(
        slug="access-review-coverage-auditor",
        title="Access Review Coverage Auditor",
        description="Vendor-neutral skill to audit access review coverage and flag stale grants or missing attestations.",
    ),
    SkillTemplate(
        slug="pipeline-flake-detector",
        title="Pipeline Flake Detector",
        description="Vendor-neutral skill to detect flaky CI jobs from historical run data and suggest stabilization actions.",
    ),
    SkillTemplate(
        slug="product-trial-conversion-explainer",
        title="Product Trial Conversion Explainer",
        description="Vendor-neutral skill to explain trial conversion changes across cohorts, channels, and onboarding paths.",
    ),
    SkillTemplate(
        slug="threat-model-gap-finder",
        title="Threat Model Gap Finder",
        description="Vendor-neutral skill to compare threat models against architecture changes and surface missing controls.",
    ),
    SkillTemplate(
        slug="invoice-anomaly-detector",
        title="Invoice Anomaly Detector",
        description="Vendor-neutral skill to flag billing anomalies in vendor invoices and produce reconciliation actions.",
    ),
    SkillTemplate(
        slug="sla-credit-calculator",
        title="SLA Credit Calculator",
        description="Vendor-neutral skill to calculate SLA credits from incident timelines and contractual thresholds.",
    ),
    SkillTemplate(
        slug="feature-request-deduplicator",
        title="Feature Request Deduplicator",
        description="Vendor-neutral skill to cluster duplicate feature requests and summarize merged customer demand.",
    ),
    SkillTemplate(
        slug="competitive-win-loss-analyzer",
        title="Competitive Win-Loss Analyzer",
        description="Vendor-neutral skill to analyze win-loss notes and extract recurring competitive themes.",
    ),
    SkillTemplate(
        slug="nps-verbatim-theme-extractor",
        title="NPS Verbatim Theme Extractor",
        description="Vendor-neutral skill to extract themes and sentiment drivers from NPS verbatim responses.",
    ),
    SkillTemplate(
        slug="billing-dispute-triage-assistant",
        title="Billing Dispute Triage Assistant",
        description="Vendor-neutral skill to triage billing disputes and recommend resolution paths with evidence checks.",
    ),
    SkillTemplate(
        slug="partner-api-health-monitor",
        title="Partner API Health Monitor",
        description="Vendor-neutral skill to monitor partner API health metrics and surface integration degradation risks.",
    ),
    SkillTemplate(
        slug="secrets-rotation-planner",
        title="Secrets Rotation Planner",
        description="Vendor-neutral skill to plan credential rotations based on age, exposure, and dependency blast radius.",
    ),
    SkillTemplate(
        slug="deployment-freeze-advisor",
        title="Deployment Freeze Advisor",
        description="Vendor-neutral skill to recommend deployment freeze windows from incident load and release risk signals.",
    ),
    SkillTemplate(
        slug="cost-anomaly-explainer",
        title="Cost Anomaly Explainer",
        description="Vendor-neutral skill to explain cloud cost anomalies by service, tag, and recent infrastructure changes.",
    ),
    SkillTemplate(
        slug="schema-migration-risk-checker",
        title="Schema Migration Risk Checker",
        description="Vendor-neutral skill to assess database schema migration risk from lock time, size, and dependency usage.",
    ),
    SkillTemplate(
        slug="ab-test-power-calculator",
        title="A/B Test Power Calculator",
        description="Vendor-neutral skill to estimate experiment power, sample size, and runtime for product experiments.",
    ),
    SkillTemplate(
        slug="renewal-churn-playbook-builder",
        title="Renewal Churn Playbook Builder",
        description="Vendor-neutral skill to build renewal save playbooks from account health and usage decline signals.",
    ),
    SkillTemplate(
        slug="compliance-evidence-collector",
        title="Compliance Evidence Collector",
        description="Vendor-neutral skill to map controls to evidence artifacts and flag audit readiness gaps.",
    ),
    SkillTemplate(
        slug="inventory-staleness-auditor",
        title="Inventory Staleness Auditor",
        description="Vendor-neutral skill to detect stale service inventory records and recommend ownership updates.",
    ),
    SkillTemplate(
        slug="queue-backlog-prioritizer",
        title="Queue Backlog Prioritizer",
        description="Vendor-neutral skill to prioritize engineering backlog items using impact, urgency, and dependency cost.",
    ),
    SkillTemplate(
        slug="marketing-attribution-sanity-checker",
        title="Marketing Attribution Sanity Checker",
        description="Vendor-neutral skill to audit marketing attribution models for double counting and channel bias.",
    ),
    SkillTemplate(
        slug="pager-noise-reduction-advisor",
        title="Pager Noise Reduction Advisor",
        description="Vendor-neutral skill to identify noisy alerts and propose paging policy improvements.",
    ),
    SkillTemplate(
        slug="data-pipeline-freshness-auditor",
        title="Data Pipeline Freshness Auditor",
        description="Vendor-neutral skill to audit warehouse table freshness and rank downstream impact of delays.",
    ),
    SkillTemplate(
        slug="license-usage-optimizer",
        title="License Usage Optimizer",
        description="Vendor-neutral skill to find underused software licenses and recommend seat right-sizing actions.",
    ),
    SkillTemplate(
        slug="customer-health-score-explainer",
        title="Customer Health Score Explainer",
        description="Vendor-neutral skill to explain customer health score movement with leading indicator breakdowns.",
    ),
    SkillTemplate(
        slug="api-rate-limit-impact-analyzer",
        title="API Rate Limit Impact Analyzer",
        description="Vendor-neutral skill to analyze rate-limit events and estimate customer-facing impact.",
    ),
    SkillTemplate(
        slug="incident-severity-calibrator",
        title="Incident Severity Calibrator",
        description="Vendor-neutral skill to calibrate incident severity from impact scope, duration, and customer tier.",
    ),
    SkillTemplate(
        slug="docs-freshness-linter",
        title="Docs Freshness Linter",
        description="Vendor-neutral skill to flag outdated documentation based on code churn and broken references.",
    ),
    SkillTemplate(
        slug="quota-forecast-builder",
        title="Quota Forecast Builder",
        description="Vendor-neutral skill to forecast sales quota attainment from pipeline stage and historical conversion.",
    ),
    SkillTemplate(
        slug="entitlement-drift-detector",
        title="Entitlement Drift Detector",
        description="Vendor-neutral skill to detect entitlement mismatches between billing, product, and access systems.",
    ),
    SkillTemplate(
        slug="synthetic-monitor-gap-finder",
        title="Synthetic Monitor Gap Finder",
        description="Vendor-neutral skill to find critical user journeys missing synthetic monitoring coverage.",
    ),
    SkillTemplate(
        slug="rollback-readiness-checker",
        title="Rollback Readiness Checker",
        description="Vendor-neutral skill to evaluate rollback readiness for releases using config, schema, and feature flags.",
    ),
    SkillTemplate(
        slug="support-macro-gap-analyzer",
        title="Support Macro Gap Analyzer",
        description="Vendor-neutral skill to find support ticket themes lacking macro coverage and draft macro candidates.",
    ),
    SkillTemplate(
        slug="vendor-sla-breach-summarizer",
        title="Vendor SLA Breach Summarizer",
        description="Vendor-neutral skill to summarize vendor SLA breaches and contract remedy options.",
    ),
    SkillTemplate(
        slug="product-feedback-router",
        title="Product Feedback Router",
        description="Vendor-neutral skill to route product feedback to owners with priority and duplicate detection.",
    ),
    SkillTemplate(
        slug="identity-provisioning-auditor",
        title="Identity Provisioning Auditor",
        description="Vendor-neutral skill to audit identity provisioning workflows for timing, scope, and policy violations.",
    ),
    SkillTemplate(
        slug="cache-invalidation-planner",
        title="Cache Invalidation Planner",
        description="Vendor-neutral skill to plan cache invalidation strategies for high-risk data updates.",
    ),
    SkillTemplate(
        slug="finops-chargeback-reporter",
        title="FinOps Chargeback Reporter",
        description="Vendor-neutral skill to produce chargeback reports with tag coverage and allocation confidence notes.",
    ),
    SkillTemplate(
        slug="error-budget-policy-linter",
        title="Error Budget Policy Linter",
        description="Vendor-neutral skill to lint SLO and error budget policies for ambiguity and enforcement gaps.",
    ),
    SkillTemplate(
        slug="customer-reference-request-triager",
        title="Customer Reference Request Triager",
        description="Vendor-neutral skill to triage reference requests by account fit, risk, and sales urgency.",
    ),
    SkillTemplate(
        slug="multi-tenant-noise-isolator",
        title="Multi-Tenant Noise Isolator",
        description="Vendor-neutral skill to isolate noisy-neighbor incidents across tenants using usage and latency signals.",
    ),
    SkillTemplate(
        slug="data-retention-enforcement-planner",
        title="Data Retention Enforcement Planner",
        description="Vendor-neutral skill to plan retention enforcement jobs with legal hold and deletion safeguards.",
    ),
    SkillTemplate(
        slug="release-train-risk-ranker",
        title="Release Train Risk Ranker",
        description="Vendor-neutral skill to rank release train candidates by dependency risk and rollback complexity.",
    ),
    SkillTemplate(
        slug="oncall-handoff-summarizer",
        title="On-Call Handoff Summarizer",
        description="Vendor-neutral skill to summarize on-call handoffs with open incidents, risks, and follow-up tasks.",
    ),
    SkillTemplate(
        slug="usage-based-pricing-simulator",
        title="Usage-Based Pricing Simulator",
        description="Vendor-neutral skill to simulate usage-based pricing scenarios and margin outcomes.",
    ),
    SkillTemplate(
        slug="privacy-dsar-triage-assistant",
        title="Privacy DSAR Triage Assistant",
        description="Vendor-neutral skill to triage data subject requests and map required systems and timelines.",
    ),
    SkillTemplate(
        slug="config-drift-detector",
        title="Config Drift Detector",
        description="Vendor-neutral skill to detect configuration drift across environments and suggest normalization actions.",
    ),
    SkillTemplate(
        slug="sales-forecast-bias-checker",
        title="Sales Forecast Bias Checker",
        description="Vendor-neutral skill to detect systematic forecast bias by rep, segment, and stage.",
    ),
    SkillTemplate(
        slug="integration-test-gap-analyzer",
        title="Integration Test Gap Analyzer",
        description="Vendor-neutral skill to find integration paths lacking automated tests after recent service changes.",
    ),
    SkillTemplate(
        slug="status-page-comms-drafter",
        title="Status Page Comms Drafter",
        description="Vendor-neutral skill to draft status page updates from incident timelines and customer impact data.",
    ),
    SkillTemplate(
        slug="warehouse-query-cost-optimizer",
        title="Warehouse Query Cost Optimizer",
        description="Vendor-neutral skill to identify expensive warehouse queries and recommend optimization actions.",
    ),
    SkillTemplate(
        slug="ai-prompt-regression-tracker",
        title="AI Prompt Regression Tracker",
        description="Vendor-neutral skill to track prompt regressions across model versions with tagged eval outcomes.",
    ),
    SkillTemplate(
        slug="procurement-rfp-comparator",
        title="Procurement RFP Comparator",
        description="Vendor-neutral skill to compare vendor RFP responses against weighted evaluation criteria.",
    ),
    SkillTemplate(
        slug="subscription-downgrade-risk-scorer",
        title="Subscription Downgrade Risk Scorer",
        description="Vendor-neutral skill to score downgrade risk from product usage and support interaction signals.",
    ),
    SkillTemplate(
        slug="mobile-crash-triage-assistant",
        title="Mobile Crash Triage Assistant",
        description="Vendor-neutral skill to triage mobile crash clusters by release, device, and customer impact.",
    ),
    SkillTemplate(
        slug="api-deprecation-impact-analyzer",
        title="API Deprecation Impact Analyzer",
        description="Vendor-neutral skill to analyze API deprecation impact on consumers and migration urgency.",
    ),
    SkillTemplate(
        slug="shift-handover-checklist-builder",
        title="Shift Handover Checklist Builder",
        description="Vendor-neutral skill to build shift handover checklists from open work, risks, and SLA exposure.",
    ),
]


def render_skill_md(skill_name: str, description: str) -> str:
    return f"""---
name: {skill_name}
description: {description}
---

## Purpose

Use this skill to process structured input and produce a concise, actionable report.

## Input

- JSON object or CSV rows with the relevant business signals.

## Output

- Structured JSON summary with findings and recommendations.
"""


def render_readme(skill_name: str, title: str) -> str:
    return f"""# {title}

Reference implementation for `{skill_name}`.

## Run

```bash
python run.py --input ../../samples/{skill_name}/input.json --output ../../samples/{skill_name}/output.json
```
"""


def render_python() -> str:
    return '''"""Reference implementation scaffold for a generated skill.""" 

from __future__ import annotations

import argparse
import json
from pathlib import Path


def run(payload: dict) -> dict:
    return {
        "status": "ok",
        "summary": "Generated skill scaffold executed successfully.",
        "input_keys": sorted(payload.keys()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    payload = json.loads(input_path.read_text())
    result = run(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def existing_slugs() -> set[str]:
    return {
        child.name
        for child in SKILLS_DIR.iterdir()
        if child.is_dir() and (child / "SKILL.md").exists()
    }


def available_templates() -> list[SkillTemplate]:
    present = existing_slugs()
    return [template for template in TEMPLATES if template.slug not in present]


def daily_selection(templates: list[SkillTemplate], day_key: str, count: int) -> list[SkillTemplate]:
    if not templates:
        return []
    start = sum(ord(char) for char in day_key) % len(templates)
    selected: list[SkillTemplate] = []
    for offset in range(len(templates)):
        if len(selected) >= count:
            break
        selected.append(templates[(start + offset) % len(templates)])
    return selected


def create_skill(template: SkillTemplate) -> bool:
    skill_name = template.slug
    skill_dir = SKILLS_DIR / skill_name
    if skill_dir.exists():
        return False

    sample_dir = SAMPLES_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    (skill_dir / "SKILL.md").write_text(render_skill_md(skill_name, template.description))
    (skill_dir / "README.md").write_text(render_readme(skill_name, template.title))
    (skill_dir / "run.py").write_text(render_python())
    (sample_dir / "input.json").write_text(
        '{"source":"daily-generator","skill":"%s"}\n' % skill_name
    )
    return True


def generate(count: int = 5) -> int:
    day_key = datetime.now(timezone.utc).strftime("%Y%m%d")
    candidates = available_templates()
    if not candidates:
        print(
            "Created 0 skill(s). All templates in the daily catalog already exist in skills/. "
            "Add more entries to TEMPLATES in scripts/generate_daily_skills.py.",
        )
        return 0

    created = 0
    for template in daily_selection(candidates, day_key, count):
        if create_skill(template):
            created += 1
            print(f"Created {template.slug}")

    remaining = len(available_templates()) - created
    if created == 0:
        print(f"Created 0 skill(s) on {day_key}. No new skills were added.")
    elif created < count:
        print(
            f"Created {created} skill(s) on {day_key}. "
            f"Only {len(candidates)} template(s) were available ({remaining} still queued in catalog).",
        )
    else:
        print(f"Created {created} skill(s) on {day_key}.")
    return created


if __name__ == "__main__":
    generate(5)
    raise SystemExit(0)
