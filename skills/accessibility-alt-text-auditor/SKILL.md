---
name: accessibility-alt-text-auditor
description: Vendor-neutral skill to audit HTML for missing or low-quality image alternative text and propose fixes.
---

## When to invoke
- You have an HTML page (or snippet) and need to improve accessibility by ensuring images have meaningful `alt` text.
- You want a quick report of missing `alt`, empty `alt`, placeholder `alt`, or filename-based `alt`.

## Inputs needed
- Path to an HTML file.
- (Optional) A JSON policy file with:
  - `ignore_src_prefixes`: list of string prefixes for images to ignore
  - `placeholder_alt_patterns`: list of regex strings to treat as placeholders

## Workflow
1. Parse the HTML and collect all `<img>` elements.
2. For each image, extract `src`, `alt`, and basic context (nearby text).
3. Classify issues:
   - `missing_alt`: no `alt` attribute
   - `empty_alt`: `alt` is present but empty/whitespace
   - `placeholder_alt`: `alt` looks like “image”, “photo”, etc.
   - `filename_alt`: `alt` appears to be a filename or URL fragment
4. Suggest an improved `alt` based on:
   - `title` attribute if present
   - file basename (lightly cleaned)
   - nearby text content (if present)
5. Output a JSON report and an optional patched HTML file.

## Output format
JSON to stdout:
- `summary`: counts by issue type
- `findings`: list of `{src, alt, issue_types, suggested_alt, context_excerpt}`

## Guardrails
- Do not claim semantic meaning you cannot infer; prefer conservative suggestions.
- Respect decorative images: if `role="presentation"` or `aria-hidden="true"`, report but do not force non-empty `alt`.
- Never add `alt` suggestions for ignored `src` prefixes.

## Reference code
`alt_text_auditor.py`
