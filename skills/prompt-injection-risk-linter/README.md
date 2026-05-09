# prompt-injection-risk-linter

Lints a prompt template (and optionally example retrieved content) for common prompt-injection and boundary risks.

## Run

```bash
python /home/user/workspace/agent-skills/skills/prompt-injection-risk-linter/prompt_injection_risk_linter.py \
  --prompt ../../samples/prompt-injection-risk-linter/prompt.txt \
  --retrieved ../../samples/prompt-injection-risk-linter/retrieved.txt \
  --output /tmp/prompt_injection_report.json
```

```bash
cat /tmp/prompt_injection_report.json
```
