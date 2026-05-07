---
name: release-notes-writer
description: Use to assemble user-facing release notes from a list of merged PRs (CSV/JSON) or by reading `git log` between two refs. Groups changes into Features / Improvements / Fixes / Breaking, drops internal-only items, links each line back to its PR, and produces both a public Markdown and a Slack-ready short version. Vendor-neutral.
---

# Release Notes Writer

## When to invoke
- "Generate release notes for v3.2."
- "What's in this release? Group changes for the changelog."
- "Draft user-facing notes between v1.4.0 and main."

## Inputs needed
1. **Source** — one of:
   - CSV / JSON of merged PRs (number, title, body, labels, author, url)
   - Two git refs (e.g. v1.4.0..HEAD) — uses `git log`
2. **Audience** — `public` (default; drops chore/internal) or `internal` (keeps everything).
3. **Version** + date.

## Workflow
1. **Ingest** the change list.
2. **Classify** each item: Feature, Improvement, Fix, Breaking, Internal.
   - Use Conventional-Commit prefixes (`feat:`, `fix:`, `chore:`, `BREAKING CHANGE`) when present.
   - Otherwise infer from labels and title verbs.
3. **Filter** out internal items if `audience=public`.
4. **Render**:
   - `RELEASE_NOTES.md` — sectioned Markdown with PR links
   - `SLACK.md` — 3-bullet TL;DR
5. **Highlight** breaking changes at the top with explicit migration callouts.

## Output format
```
## Highlights
## Breaking changes
## New features
## Improvements
## Bug fixes
## Internal (omitted from public notes)
```

## Guardrails
- Never invent or rewrite a PR title beyond minor copy editing.
- Always link back to the PR number / URL.
- Breaking changes get their own section even if there's only one.

## Reference code
`generate.py` reads CSV/JSON or `git log`, classifies, and writes both Markdown outputs.
