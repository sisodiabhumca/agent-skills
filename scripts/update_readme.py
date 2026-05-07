"""Regenerate README.md skill table from the contents of skills/.

Reads the YAML frontmatter `description` from each `skills/<name>/SKILL.md`
and writes a sorted, auto-generated table between two markers in README.md.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
README = ROOT / "README.md"

START = "<!-- SKILLS-TABLE-START -->"
END = "<!-- SKILLS-TABLE-END -->"


def read_description(skill_md: Path) -> str:
    text = skill_md.read_text(errors="ignore")
    m = re.search(r"^---\s*\n(.*?)^---\s*\n", text, flags=re.DOTALL | re.MULTILINE)
    if not m:
        return ""
    fm = m.group(1)
    dm = re.search(r"^description:\s*(.+?)\s*$", fm, flags=re.MULTILINE)
    if not dm:
        return ""
    desc = dm.group(1).strip()
    # Strip surrounding quotes if present
    if (desc.startswith('"') and desc.endswith('"')) or (desc.startswith("'") and desc.endswith("'")):
        desc = desc[1:-1]
    # First sentence only, to keep the row tight
    first = re.split(r"(?<=[.!?])\s+", desc, maxsplit=1)[0]
    return first.strip()


def build_table() -> str:
    rows = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        sm = d / "SKILL.md"
        if not sm.exists():
            continue
        desc = read_description(sm) or "_(no description)_"
        # Escape pipes inside descriptions so the Markdown table stays valid
        desc = desc.replace("|", "\\|")
        rows.append(f"| [`{d.name}`](./skills/{d.name}) | {desc} |")
    if not rows:
        return "_(no skills yet)_"
    header = ["| Skill | Description |", "|---|---|"]
    return "\n".join(header + rows)


def update_readme() -> int:
    text = README.read_text()
    if START not in text or END not in text:
        print("ERROR: README is missing SKILLS-TABLE markers.", file=sys.stderr)
        return 1
    table = build_table()
    new_text = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        f"{START}\n{table}\n{END}",
        text,
        flags=re.DOTALL,
    )
    count = sum(1 for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").exists())
    new_text = re.sub(
        r"<!-- SKILLS-COUNT-START -->.*?<!-- SKILLS-COUNT-END -->",
        f"<!-- SKILLS-COUNT-START -->{count}<!-- SKILLS-COUNT-END -->",
        new_text,
        flags=re.DOTALL,
    )
    if new_text != text:
        README.write_text(new_text)
        print(f"README updated. Skills: {count}")
    else:
        print(f"README already up to date. Skills: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(update_readme())
