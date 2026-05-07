# release-notes-writer

Generate sectioned release notes (Markdown) and a Slack TL;DR from a list of merged PRs or a git range.

## Run on the bundled sample

```bash
python generate.py --prs ../../samples/release-notes-writer/sample_prs.csv --version 3.2.0 --date 2025-05-07
```

Outputs `RELEASE_NOTES.md` (public, full sections) and `SLACK.md` (3-bullet summary).

## Use your own data

CSV columns (header required): `number,title,body,labels,author,url`.
JSON: array of objects with the same keys.

## From git directly

```bash
python generate.py --git-range v1.4.0..HEAD --version 1.5.0
```

Reads `git log` (no merges), classifies via Conventional-Commit prefixes.

## Audience

- `--audience public` (default) drops chore/internal items.
- `--audience internal` keeps everything in a separate section.

Stdlib only, no external dependencies.

## Sample data

Sample inputs for this skill live in `../../samples/release-notes-writer/` (kept outside the skill folder so security scanners don't need to handle non-code data).
