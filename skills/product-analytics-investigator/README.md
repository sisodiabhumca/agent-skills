# product-analytics-investigator

Investigate product metric changes in Amplitude or Mixpanel and produce a root-cause memo.

## Run

```bash
pip install -r requirements.txt
python investigate.py --source csv --csv sample_events.csv \
  --steps view_pricing start_checkout purchase \
  --segment platform --current-days 7 --prior-days 7 \
  --end 2026-05-07T00:00:00Z
```

For live data, set credentials and run:

```bash
export AMPLITUDE_API_KEY=... AMPLITUDE_SECRET_KEY=...
python investigate.py --source amplitude --steps view_pricing start_checkout purchase
```

See [SKILL.md](./SKILL.md) for the full skill definition.
