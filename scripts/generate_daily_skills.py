"""Create 5 new skill scaffolds for the current UTC day.

This script is deterministic per day and idempotent:
- It generates exactly `count` unique skill names for the day.
- If a generated skill already exists, it is skipped.
- It writes SKILL.md, README.md, and run.py for each new skill.
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


TEMPLATES = [
    SkillTemplate(
        slug="customer-churn-risk-ranker",
        title="Customer Churn Risk Ranker",
        description="Vendor-neutral skill to score customer churn risk from account signals and produce prioritized retention actions.",
    ),
    SkillTemplate(
        slug="release-risk-checklist-builder",
        title="Release Risk Checklist Builder",
        description="Vendor-neutral skill to generate a release risk checklist from scope, dependencies, and rollout constraints.",
    ),
    SkillTemplate(
        slug="api-error-budget-tracker",
        title="API Error Budget Tracker",
        description="Vendor-neutral skill to analyze API reliability metrics and summarize error budget burn with mitigation guidance.",
    ),
    SkillTemplate(
        slug="sales-call-objection-clusterer",
        title="Sales Call Objection Clusterer",
        description="Vendor-neutral skill to cluster sales call objections and extract response patterns for enablement.",
    ),
    SkillTemplate(
        slug="runbook-freshness-auditor",
        title="Runbook Freshness Auditor",
        description="Vendor-neutral skill to identify stale runbooks and recommend updates based on recent incidents and ownership gaps.",
    ),
    SkillTemplate(
        slug="forecast-assumption-drift-checker",
        title="Forecast Assumption Drift Checker",
        description="Vendor-neutral skill to compare forecast assumptions over time and flag high-impact drift.",
    ),
    SkillTemplate(
        slug="roadmap-dependency-heatmap",
        title="Roadmap Dependency Heatmap",
        description="Vendor-neutral skill to map roadmap dependencies and surface delivery risk concentrations.",
    ),
    SkillTemplate(
        slug="incident-comms-clarity-linter",
        title="Incident Comms Clarity Linter",
        description="Vendor-neutral skill to lint incident communications for clarity, completeness, and stakeholder alignment.",
    ),
    SkillTemplate(
        slug="onboarding-dropoff-explainer",
        title="Onboarding Dropoff Explainer",
        description="Vendor-neutral skill to analyze onboarding funnel dropoff and propose prioritized interventions.",
    ),
    SkillTemplate(
        slug="security-exception-expiry-tracker",
        title="Security Exception Expiry Tracker",
        description="Vendor-neutral skill to track security exception expirations and generate remediation reminders.",
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


def daily_templates(day_key: str, count: int) -> list[SkillTemplate]:
    start = sum(ord(ch) for ch in day_key) % len(TEMPLATES)
    picks = []
    for i in range(count):
        picks.append(TEMPLATES[(start + i) % len(TEMPLATES)])
    return picks


def create_skill(day_key: str, idx: int, template: SkillTemplate) -> bool:
    skill_name = f"{template.slug}-{day_key}-{idx:02d}"
    skill_dir = SKILLS_DIR / skill_name
    if skill_dir.exists():
        return False

    sample_dir = SAMPLES_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    (skill_dir / "SKILL.md").write_text(render_skill_md(skill_name, template.description))
    (skill_dir / "README.md").write_text(render_readme(skill_name, template.title))
    (skill_dir / "run.py").write_text(render_python())
    (sample_dir / "input.json").write_text('{"source":"daily-generator","day":"%s"}\n' % day_key)
    return True


def generate(count: int = 5) -> int:
    day_key = datetime.now(timezone.utc).strftime("%Y%m%d")
    created = 0
    for idx, template in enumerate(daily_templates(day_key, count), start=1):
        if create_skill(day_key, idx, template):
            created += 1
    print(f"Created {created} skill(s) for {day_key}.")
    return created


if __name__ == "__main__":
    generate(5)
