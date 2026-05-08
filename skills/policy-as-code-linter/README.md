# policy-as-code-linter

Vendor-neutral skill to lint a simple YAML policy file for completeness and risky patterns.

## Run on the bundled sample

```bash
python policy_as_code_linter.py \
  --input ../../samples/policy-as-code-linter/policy.yaml \
  --json-out /tmp/policy_lint_report.json
```
