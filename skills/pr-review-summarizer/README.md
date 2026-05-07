# pr-review-summarizer

Read a unified diff (file, stdin, or fetched via `gh` / `glab`) and produce a structured PR review brief.

## Run

```bash
python review.py --diff ../../samples/pr-review-summarizer/sample.diff
# or
gh pr diff 42 | python review.py --diff -
# or
python review.py --gh-pr owner/repo#42
```

See [SKILL.md](./SKILL.md).

## Sample data

Sample inputs for this skill live in `../../samples/pr-review-summarizer/` (kept outside the skill folder so security scanners don't need to handle non-code data).
