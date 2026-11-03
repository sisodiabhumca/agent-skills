#!/usr/bin/env python3
"""Build docs/skills.json for the GitHub Pages skill playground."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
OUT = ROOT / "docs" / "skills.json"

CATEGORY_RULES = [
    (
        "Product & Growth",
        [
            "product",
            "growth",
            "experiment",
            "funnel",
            "onboarding",
            "feature",
            "roadmap",
            "adoption",
            "trial",
            "churn",
            "pricing",
            "utm",
            "marketing",
            "cohort",
        ],
    ),
    (
        "Data & Analytics",
        [
            "data",
            "analytics",
            "kpi",
            "metric",
            "schema",
            "etl",
            "warehouse",
            "lineage",
            "contract",
            "sqlite",
            "sql",
            "forecast",
        ],
    ),
    (
        "Engineering & Platform",
        [
            "api",
            "release",
            "pipeline",
            "deploy",
            "architecture",
            "dependency",
            "ci",
            "http",
            "json",
            "feature-flag",
            "cache",
            "webhook",
            "migration",
            "config",
        ],
    ),
    (
        "Security & Compliance",
        [
            "security",
            "privacy",
            "compliance",
            "pii",
            "access",
            "identity",
            "prompt-injection",
            "sbom",
            "license",
            "guardrail",
            "consent",
            "audit",
            "redaction",
            "threat",
        ],
    ),
    (
        "Sales & CRM",
        [
            "sales",
            "crm",
            "opportunity",
            "objection",
            "quota",
            "renewal",
            "win-loss",
            "reference",
            "pipeline-stage",
        ],
    ),
    (
        "Support & CX",
        [
            "support",
            "sla",
            "macro",
            "ticket",
            "customer",
            "ces",
            "nps",
            "deflection",
            "interview",
        ],
    ),
    (
        "Finance & FinOps",
        [
            "billing",
            "cost",
            "spend",
            "saas",
            "invoice",
            "finops",
            "budget",
            "discount",
            "revenue",
            "license-usage",
        ],
    ),
    (
        "Incidents & Ops",
        [
            "incident",
            "postmortem",
            "oncall",
            "runbook",
            "alert",
            "pager",
            "rca",
            "timeline",
            "uptime",
            "status-page",
        ],
    ),
]


def categorize(skill_id: str, description: str) -> str:
    blob = f"{skill_id} {description}".lower()
    for label, keys in CATEGORY_RULES:
        if any(key in blob for key in keys):
            return label
    return "Operations"


def parse_skill(skill_dir: Path) -> dict | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return None
    text = skill_md.read_text(errors="ignore")
    match = re.search(r"^---\s*\n(.*?)^---\s*\n(.*)$", text, flags=re.S | re.M)
    name = skill_dir.name
    description = ""
    body = text.strip()
    if match:
        frontmatter, body = match.group(1), match.group(2).strip()
        description_match = re.search(r"^description:\s*(.+?)\s*$", frontmatter, flags=re.M)
        name_match = re.search(r"^name:\s*(.+?)\s*$", frontmatter, flags=re.M)
        if description_match:
            description = description_match.group(1).strip().strip("\"'")
        if name_match:
            name = name_match.group(1).strip().strip("\"'")
    return {
        "id": skill_dir.name,
        "name": name,
        "description": description,
        "category": categorize(skill_dir.name, description),
        "path": f"skills/{skill_dir.name}/SKILL.md",
        "install": (
            "npx skills add https://github.com/sisodiabhumca/agent-skills "
            f"--skill {skill_dir.name}"
        ),
        "github": f"https://github.com/sisodiabhumca/agent-skills/tree/main/skills/{skill_dir.name}",
        "body": body,
    }


def main() -> int:
    skills = []
    for child in sorted(SKILLS_DIR.iterdir()):
        if not child.is_dir():
            continue
        parsed = parse_skill(child)
        if parsed:
            skills.append(parsed)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "repo": "sisodiabhumca/agent-skills",
        "count": len(skills),
        "categories": dict(Counter(skill["category"] for skill in skills)),
        "skills": skills,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Wrote {OUT} with {len(skills)} skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
