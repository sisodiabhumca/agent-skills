---
name: docx-style-auditor
description: Audits .docx documents for vendor-neutral style consistency issues (headings, spacing) and outputs an actionable report.
---

## When to invoke
- You receive Word documents from multiple authors and need consistent formatting.
- You want a checklist of style issues before publishing or exporting to PDF.

## Inputs needed
- `--input`: Path to a `.docx` file.
- Optional: `--out`: Path to write a JSON report.

## Workflow
1. Read `word/document.xml` from the `.docx` zip.
2. Identify paragraph styles (`w:pStyle`) and detect:
   - direct formatting overrides (e.g., explicit font size on headings)
   - inconsistent heading level jumps (e.g., Heading 1 -> Heading 3)
   - excessive empty paragraphs
3. Produce counts and examples with paragraph text snippets.

## Output format
JSON with:
- `summary`: counts per issue type
- `issues`: list of `{issue_type, severity, location, excerpt}`

## Guardrails
- Read-only: never modify the input document.
- Best-effort parsing; if namespaces/parts are missing, fail with a clear error.
- Vendor-neutral: focus on OpenXML structure, not a specific Word version.

## Reference code
Use `docx_style_auditor.py`.
