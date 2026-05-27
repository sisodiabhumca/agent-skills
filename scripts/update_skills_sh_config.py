"""Regenerate skills.sh.json from the contents of skills/."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
CONFIG = ROOT / "skills.sh.json"


def skill_names() -> list[str]:
    return sorted(
        path.name
        for path in SKILLS_DIR.iterdir()
        if path.is_dir() and (path / "SKILL.md").exists()
    )


def main() -> int:
    names = skill_names()
    data = {
        "$schema": "https://skills.sh/schemas/skills.sh.schema.json",
        "notGrouped": "bottom",
        "groupings": [
            {
                "title": "Agent Skills",
                "description": "Vendor-neutral skills for product, data, engineering, security, support, and operations workflows.",
                "skills": names,
            }
        ],
    }
    text = json.dumps(data, indent=2) + "\n"
    if CONFIG.exists() and CONFIG.read_text() == text:
        print(f"skills.sh.json already up to date. Skills: {len(names)}")
        return 0
    CONFIG.write_text(text)
    print(f"skills.sh.json updated. Skills: {len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
