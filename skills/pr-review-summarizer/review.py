"""PR Review Summarizer.

Reads a unified diff and produces a structured review.

Usage:
  python review.py --diff sample.diff
  python review.py --diff -                          # read from stdin
  python review.py --gh-pr owner/repo#123            # uses `gh pr diff`
  python review.py --glab-mr group/proj!45           # uses `glab mr diff`
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


SECURITY_PATHS = re.compile(
    r"(auth|login|password|secret|token|crypt|jwt|oauth|saml|signing|key/|\.env|policy|permissions|iam|rbac)",
    re.IGNORECASE,
)
SCHEMA_PATHS = re.compile(r"(migrations?/|schema\.|alembic|/sql/|\.sql\b|prisma/schema)", re.IGNORECASE)
DEP_PATHS = re.compile(r"(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|requirements.*\.txt|pyproject\.toml|poetry\.lock|go\.mod|go\.sum|Cargo\.toml|Cargo\.lock|Gemfile.*|pom\.xml|build\.gradle.*)", re.IGNORECASE)
TEST_PATHS = re.compile(r"(/tests?/|_test\.|\.spec\.|\.test\.|\bspec/)", re.IGNORECASE)
DOC_PATHS = re.compile(r"(\.md$|/docs?/|README)", re.IGNORECASE)
CONFIG_PATHS = re.compile(r"(\.ya?ml$|\.toml$|\.ini$|\.conf$|Dockerfile|\.tf$|\.tfvars$)", re.IGNORECASE)


@dataclass
class FileChange:
    path: str
    added: int = 0
    removed: int = 0
    is_new: bool = False
    is_deleted: bool = False
    hunks: list[str] = field(default_factory=list)

    def category(self) -> str:
        p = self.path
        if SCHEMA_PATHS.search(p):
            return "schema"
        if DEP_PATHS.search(p):
            return "dependencies"
        if SECURITY_PATHS.search(p):
            return "security-sensitive"
        if TEST_PATHS.search(p):
            return "tests"
        if DOC_PATHS.search(p):
            return "docs"
        if CONFIG_PATHS.search(p):
            return "config"
        return "code"

    def risk(self) -> tuple[str, list[str]]:
        reasons: list[str] = []
        cat = self.category()
        score = 0
        if cat == "schema":
            score += 3; reasons.append("schema/migration change")
        if cat == "security-sensitive":
            score += 3; reasons.append("touches auth / crypto / policy")
        if cat == "dependencies":
            score += 2; reasons.append("dependency manifest change")
        churn = self.added + self.removed
        if churn >= 400:
            score += 3; reasons.append(f"large churn ({churn} lines)")
        elif churn >= 150:
            score += 1; reasons.append(f"moderate churn ({churn} lines)")
        if self.is_new and cat == "code":
            score += 1; reasons.append("new code path")
        if self.is_deleted:
            score += 1; reasons.append("file deleted")
        level = "High" if score >= 4 else ("Medium" if score >= 2 else "Low")
        return level, reasons


def parse_diff(text: str) -> list[FileChange]:
    files: list[FileChange] = []
    cur: FileChange | None = None
    for line in text.splitlines():
        if line.startswith("diff --git"):
            if cur:
                files.append(cur)
            m = re.match(r"diff --git a/(.+?) b/(.+)$", line)
            cur = FileChange(path=m.group(2) if m else "(unknown)")
        elif line.startswith("new file mode") and cur:
            cur.is_new = True
        elif line.startswith("deleted file mode") and cur:
            cur.is_deleted = True
        elif line.startswith("@@") and cur:
            cur.hunks.append(line)
        elif line.startswith("+") and not line.startswith("+++") and cur:
            cur.added += 1
        elif line.startswith("-") and not line.startswith("---") and cur:
            cur.removed += 1
    if cur:
        files.append(cur)
    return files


def fetch_gh(spec: str) -> str:
    # spec: owner/repo#NUMBER
    m = re.match(r"(.+?)#(\d+)$", spec)
    if not m:
        raise SystemExit("--gh-pr expects owner/repo#NUMBER")
    repo, num = m.group(1), m.group(2)
    return subprocess.check_output(["gh", "pr", "diff", num, "--repo", repo], text=True)


def fetch_glab(spec: str) -> str:
    # spec: group/project!NUMBER
    m = re.match(r"(.+?)!(\d+)$", spec)
    if not m:
        raise SystemExit("--glab-mr expects group/project!NUMBER")
    repo, num = m.group(1), m.group(2)
    return subprocess.check_output(["glab", "mr", "diff", num, "--repo", repo], text=True)


def render(files: list[FileChange]) -> str:
    total_add = sum(f.added for f in files)
    total_rem = sum(f.removed for f in files)
    by_cat: dict[str, list[FileChange]] = {}
    for f in files:
        by_cat.setdefault(f.category(), []).append(f)

    risks = sorted(
        [(f, *f.risk()) for f in files],
        key=lambda x: {"High": 0, "Medium": 1, "Low": 2}[x[1]],
    )
    high = [r for r in risks if r[1] == "High"]
    has_tests = any(f.category() == "tests" for f in files)
    code_files = [f for f in files if f.category() == "code"]

    lines = [
        "# Pull Request Review Brief",
        "",
        "## TL;DR",
        f"- {len(files)} files changed: **+{total_add} / -{total_rem}** lines.",
        f"- Categories: " + ", ".join(f"{k} ({len(v)})" for k, v in sorted(by_cat.items())),
        f"- High-risk hotspots: **{len(high)}**.",
        f"- Test files included: **{'yes' if has_tests else 'no'}**.",
        "",
        "## Risk hotspots (ranked)",
        "| File | Risk | Reasons | +/- |",
        "|---|---|---|---|",
    ]
    for f, level, reasons in risks:
        if level == "Low" and len(lines) > 25:
            break
        lines.append(f"| `{f.path}` | **{level}** | {'; '.join(reasons) or '—'} | +{f.added}/-{f.removed} |")

    lines += ["", "## Files changed (summary)"]
    for cat, items in sorted(by_cat.items()):
        lines.append(f"- **{cat}** ({len(items)}): " + ", ".join(f"`{f.path}`" for f in items[:8]) + (" …" if len(items) > 8 else ""))

    lines += ["", "## Missing test coverage"]
    if not code_files:
        lines.append("- No production-code changes detected.")
    elif not has_tests:
        lines.append("- Production code changed but **no test files in the diff** — request tests before merge.")
    else:
        lines.append("- Test files are present. Verify the new code paths in: " + ", ".join(f"`{f.path}`" for f in code_files[:5]))

    lines += ["", "## Reviewer questions"]
    if any(f.category() == "schema" for f in files):
        lines.append("- Is this migration backward-compatible? What is the rollback plan?")
    if any(f.category() == "security-sensitive" for f in files):
        lines.append("- Has security/privacy review signed off on the auth / policy changes?")
    if any(f.category() == "dependencies" for f in files):
        lines.append("- Were the new/updated dependencies vetted for license + CVEs?")
    if not has_tests and code_files:
        lines.append("- Why no unit tests for the new behavior? What's the test plan?")
    lines.append("- What is the blast radius if this rolls back? Any feature flag?")

    lines += [
        "",
        "## Suggested follow-ups",
        "- [ ] Add tests covering the new code paths above.",
        "- [ ] Update relevant runbook / README if behavior changed.",
        "- [ ] Confirm observability (logs, metrics, alerts) for new behavior.",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--diff", help="Path to a unified diff, or - for stdin")
    src.add_argument("--gh-pr", help="owner/repo#NUMBER (uses gh CLI)")
    src.add_argument("--glab-mr", help="group/project!NUMBER (uses glab CLI)")
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    if args.diff:
        text = sys.stdin.read() if args.diff == "-" else Path(args.diff).read_text(errors="ignore")
    elif args.gh_pr:
        text = fetch_gh(args.gh_pr)
    else:
        text = fetch_glab(args.glab_mr)

    files = parse_diff(text)
    body = render(files)
    if args.out == "-":
        print(body)
    else:
        Path(args.out).write_text(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
