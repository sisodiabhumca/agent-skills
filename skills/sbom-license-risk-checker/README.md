# sbom-license-risk-checker

Check a CycloneDX SBOM against a vendor-neutral license policy and emit a JSON risk report.

## Run

```bash
python check_sbom_licenses.py \
  --sbom "../../samples/sbom-license-risk-checker/sbom.json" \
  --policy "../../samples/sbom-license-risk-checker/policy.json" \
  --out "/tmp/sbom_license_report.json"
```
