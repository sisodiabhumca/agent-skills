# api-contract-diff

Compares two OpenAPI 3 JSON specs and produces a change report.

## Run on sample

```bash
python skills/api-contract-diff/api_contract_diff.py \
  --old ../../samples/api-contract-diff/openapi_old.json \
  --new ../../samples/api-contract-diff/openapi_new.json \
  --out /tmp/api_contract_diff_report.json

cat /tmp/api_contract_diff_report.json
```
