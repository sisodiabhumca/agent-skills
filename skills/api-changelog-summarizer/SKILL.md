---
name: api-changelog-summarizer
description: Vendor-neutral skill to compare two OpenAPI specs and summarize breaking and non-breaking API changes.
---

## When to invoke
- You maintain an API and need a release note / changelog from spec changes.
- You need to assess whether an API update is breaking.

## Inputs needed
- `--old_spec`: Path to an old OpenAPI spec (JSON).
- `--new_spec`: Path to a new OpenAPI spec (JSON).
- `--out_md`: Path to write a markdown changelog.

## Workflow
1. Parse both OpenAPI specs.
2. Build an operation map keyed by `(method, path)`.
3. Compare:
   - Added/removed paths or methods.
   - Request body requiredness.
   - Parameter additions/removals and requiredness changes.
   - Response status code additions/removals.
4. Classify changes:
   - Breaking: removed operations, removed required params, made body required, removed response codes.
   - Non-breaking: added optional params, added response codes, added operations.
5. Emit a changelog markdown with sections and bullet lists.

## Output format
- Markdown file with:
  - `## Breaking changes`
  - `## Non-breaking changes`
  - `## Notes / limitations`

## Guardrails
- This is structural diffing; it does not fully validate schema compatibility.
- Only JSON OpenAPI files are supported by the reference code.

## Reference code
- `api_changelog_summarizer.py`
