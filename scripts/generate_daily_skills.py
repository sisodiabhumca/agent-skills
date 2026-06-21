"""Create 5 new skill scaffolds per UTC day from a rotating template catalog.

Skill directories use stable slugs only (for example `sales-call-objection-clusterer`).
Each run picks five templates that are not already present in `skills/`, starting
from a day-rotated offset in the catalog.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
SAMPLES_DIR = ROOT / "samples"
TEMPLATES_FILE = ROOT / "scripts" / "skill_templates.json"


@dataclass(frozen=True)
class SkillTemplate:
    slug: str
    title: str
    description: str


def load_templates() -> list[SkillTemplate]:
    """Load templates from the JSON file."""
    if not TEMPLATES_FILE.exists():
        return []
    with open(TEMPLATES_FILE) as f:
        data = json.load(f)
    return [SkillTemplate(**item) for item in data]


def save_templates(templates: list[SkillTemplate]) -> None:
    """Save templates to the JSON file."""
    data = [{"slug": t.slug, "title": t.title, "description": t.description} for t in templates]
    with open(TEMPLATES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def generate_new_templates(count: int = 5) -> list[SkillTemplate]:
    """Generate new skill templates using free LLM API (Groq)."""
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Warning: GROQ_API_KEY or OPENAI_API_KEY not set. Cannot generate new templates.")
        return []

    try:
        import openai
    except ImportError:
        print("Warning: openai package not installed. Run: pip install openai")
        return []

    # Use Groq for free tier with open-source models
    base_url = os.environ.get("GROQ_API_KEY", "")
    if base_url:
        client = openai.OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        model = "llama-3.3-70b-versatile"  # Free model on Groq
    else:
        client = openai.OpenAI(api_key=api_key)
        model = "gpt-4o-mini"  # Fallback to cheapest OpenAI model

    existing_slugs_set = {t.slug for t in load_templates()}
    existing_slugs_set.update(existing_slugs())

    prompt = f"""Generate {count} new vendor-neutral skill templates for an AI agent skills catalog.

Each template should have:
- slug: a kebab-case identifier (e.g., "api-rate-limit-analyzer")
- title: a human-readable title (e.g., "API Rate Limit Analyzer")
- description: a concise description starting with "Vendor-neutral skill to..."

The skills should be practical, business-focused tools similar to these existing examples:
- incident-postmortem-builder
- customer-churn-risk-ranker
- data-contract-validator
- feature-flag-rollout-planner
- compliance-evidence-collector

Avoid these existing slugs: {', '.join(sorted(existing_slugs_set))}

Return ONLY valid JSON in this exact format:
[
  {{"slug": "example-slug", "title": "Example Title", "description": "Vendor-neutral skill to..."}},
  ...
]
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        content = response.choices[0].message.content.strip()
        
        # Parse JSON response
        new_data = json.loads(content)
        new_templates = [SkillTemplate(**item) for item in new_data]
        
        # Filter out any that already exist
        unique_templates = [t for t in new_templates if t.slug not in existing_slugs_set]
        
        if unique_templates:
            print(f"Generated {len(unique_templates)} new skill templates via {model}.")
        else:
            print("No unique new templates generated.")
        
        return unique_templates
    except Exception as e:
        print(f"Error generating templates: {e}")
        return []


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
    templates = load_templates()
    return [template for template in templates if template.slug not in present]


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
    
    # If no templates available, try to generate new ones
    if not candidates:
        print("No templates available. Attempting to generate new ones...")
        new_templates = generate_new_templates(count)
        if new_templates:
            # Add new templates to the file
            existing_templates = load_templates()
            all_templates = existing_templates + new_templates
            save_templates(all_templates)
            candidates = available_templates()
        
        if not candidates:
            print(
                "Created 0 skill(s). All templates in the daily catalog already exist in skills/. "
                "Could not generate new templates (GROQ_API_KEY or OPENAI_API_KEY not set or API error).",
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
