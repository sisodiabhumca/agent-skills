# oncall-runbook-executor

Execute a YAML runbook step by step with prechecks, confirmations, and a Markdown log.

## Run

```bash
# Safe dry-run (default) — prints commands but doesn't execute
python runbook.py --runbook sample_runbook.yml

# Actually run, skipping confirm prompts
python runbook.py --runbook sample_runbook.yml --mode execute --yes
```

See [SKILL.md](./SKILL.md).
