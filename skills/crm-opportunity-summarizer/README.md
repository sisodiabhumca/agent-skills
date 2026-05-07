# crm-opportunity-summarizer

Pull opportunities from Salesforce, HubSpot, or CSV and produce a deal brief with risks + next-best-action.

## Run

```bash
python summarize.py --source csv --csv ../../samples/crm-opportunity-summarizer/sample/opportunities.csv
```

Live:

```bash
export SFDC_INSTANCE=https://your.my.salesforce.com SFDC_TOKEN=...
python summarize.py --source sfdc
```

See [SKILL.md](./SKILL.md).

## Sample data

Sample inputs for this skill live in `../../samples/crm-opportunity-summarizer/` (kept outside the skill folder so security scanners don't need to handle non-code data).
