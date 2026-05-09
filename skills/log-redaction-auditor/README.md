# log-redaction-auditor

Audits a log file for likely secrets and PII, producing a JSON report.

## Run

```bash
python /home/user/workspace/agent-skills/skills/log-redaction-auditor/log_redaction_auditor.py \
  --input ../../samples/log-redaction-auditor/sample.log \
  --output /tmp/log_redaction_report.json
```

```bash
cat /tmp/log_redaction_report.json
```
