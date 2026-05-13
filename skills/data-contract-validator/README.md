# data-contract-validator

Validate JSON data against a lightweight, vendor-neutral contract and emit a JSON validation report.

## Run

```bash
python validate_contract.py \
  --contract "../../samples/data-contract-validator/contract.json" \
  --data "../../samples/data-contract-validator/records.jsonl" \
  --out "/tmp/contract_report.json"
```
