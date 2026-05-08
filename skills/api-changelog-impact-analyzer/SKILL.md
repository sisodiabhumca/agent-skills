---
name: api-changelog-impact-analyzer
description: Vendor-neutral skill for analyzing an API changelog and identifying likely breaking changes and downstream impacts.
---

## When to invoke
- You have API release notes/changelog text (Markdown) from any provider.
- You need to identify potentially breaking changes and what client code to review.
- You want a vendor-neutral heuristic analysis (not tied to any specific API platform).

## Inputs needed
- Path to a changelog markdown/text file.
- (Optional) A list of client endpoints your app uses (JSON) to cross-check.

## Workflow
1. Parse changelog into bullet items and headings.
2. Classify each item into:
   - breaking (removal, rename, required fields, auth changes)
   - behavior change (defaults, limits, ordering)
   - additive (new fields/endpoints)
   - deprecation
3. Extract impacted surfaces (endpoint paths, field names) via regex heuristics.
4. If a client-usage file is provided, highlight overlaps.
5. Output a prioritized action list.

## Output format
- Markdown summary to stdout.
- JSON report (optional) with categorized items and detected impacts.

## Guardrails
- Heuristic only; do not claim completeness.
- Do not infer security posture; only flag explicit auth/scope changes mentioned.

## Reference code
- `api_changelog_impact_analyzer.py`
