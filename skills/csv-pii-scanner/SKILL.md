---
name: csv-pii-scanner
description: Vendor-neutral skill to scan CSV exports for likely PII columns and risky values, producing a remediation-focused report.
---

## When to invoke
- When reviewing CSV exports before sharing externally.
- When building a data-loss-prevention (DLP) checklist for analytics datasets.

## Inputs needed
- `--input`: Path to a CSV file.
- Optional `--out`: Path to write a JSON report.
- Optional `--max-rows`: Max rows to sample (default 2000).

## Workflow
1. Read CSV headers and sample up to N rows.
2. For each column, score risk using:
   - Header keywords (email, phone, ssn, address, dob, name).
   - Value patterns (email-like, phone-like, IP address, credit card-like, SSN-like).
3. Output suspected PII columns with examples (redacted) and suggested remediation.

## Output format
JSON with:
- `suspected_columns`: list of `{column, risk, reasons, examples_redacted}`.
- `summary`: counts by risk.

## Guardrails
- Redact example values in output.
- Use heuristics only; results are probabilistic.

## Reference code
- `csv_pii_scanner.py`
