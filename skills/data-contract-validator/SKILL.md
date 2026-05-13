---
name: data-contract-validator
description: Vendor-neutral skill to validate JSON records against a lightweight data contract (schema + rules) and produce a validation report.
---

## When to invoke
- You receive JSON lines / JSON arrays from another system and need to ensure they meet a contract.
- You want a machine-readable report of missing fields, type mismatches, and simple rule violations.

## Inputs needed
- `--contract`: path to a contract JSON file describing fields, requiredness, and simple constraints.
- `--data`: path to a JSON file (either an array of objects or JSON Lines).

Contract format (example)
- `fields`: object keyed by field name with:
  - `type`: one of `string|number|integer|boolean|object|array|null`
  - `required`: true/false
  - `min_length` / `max_length` (strings)
  - `min` / `max` (numbers)
  - `regex` (strings)
- `rules`: list of cross-field rules:
  - `name`
  - `if`: list of conditions (`field`, `op`, `value`)
  - `then`: list of requirements (`field`, `op`, `value`)

## Workflow
1. Load contract.
2. Stream records from the data file.
3. Validate each record:
   - Required fields present
   - Types match
   - Field constraints pass
   - Cross-field rules pass
4. Emit a JSON report with counts and per-record errors.

## Output format
JSON:
- `summary`: totals + error counts
- `errors`: list of `{index, record_id, field, code, message}`

## Guardrails
- Do not mutate the input data.
- Keep error messages deterministic.
- Validate types conservatively (e.g., do not coerce strings to numbers).

## Reference code
`validate_contract.py`
