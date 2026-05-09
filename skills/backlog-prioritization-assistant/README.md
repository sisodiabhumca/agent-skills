# backlog-prioritization-assistant

Ranks backlog items from a CSV using RICE, WSJF, or a simple impact/effort ratio, and writes a JSON report.

## Run

```bash
python /home/user/workspace/agent-skills/skills/backlog-prioritization-assistant/backlog_prioritization_assistant.py \
  --input ../../samples/backlog-prioritization-assistant/backlog.csv \
  --method rice \
  --output /tmp/backlog_ranked.json
```

```bash
cat /tmp/backlog_ranked.json
```
