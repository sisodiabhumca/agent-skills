# accessibility-alt-text-auditor

Audit an HTML file for images with missing or low-quality `alt` text, and emit a JSON report.

## Run

```bash
python alt_text_auditor.py \
  --html "../../samples/accessibility-alt-text-auditor/page.html" \
  --policy "../../samples/accessibility-alt-text-auditor/policy.json" \
  --patched-out "/tmp/patched.html" \
  --report-out "/tmp/alt_audit_report.json"
```
