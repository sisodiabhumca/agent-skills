# cloud-cost-tag-coverage-auditor

Audit cloud resource export data for missing/invalid cost allocation tags and output a vendor-neutral remediation plan.

## Run

```bash
python cloud_cost_tag_coverage_auditor.py \
  --input ../../samples/cloud-cost-tag-coverage-auditor/resources.csv \
  --policy ../../samples/cloud-cost-tag-coverage-auditor/policy.json
```

## Samples
- Resources CSV: `../../samples/cloud-cost-tag-coverage-auditor/resources.csv`
- Policy JSON: `../../samples/cloud-cost-tag-coverage-auditor/policy.json`
