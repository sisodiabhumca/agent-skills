# dependency-vuln-triager

Triage scanner output (`npm audit`, `pip-audit`, OSV-Scanner, or generic JSON) into a ranked, deduplicated action list grouped by package.

## Run on the bundled sample

```bash
python triage.py --input sample_audit.json --reachable sample_reachable.txt --prod-only
```

Outputs `TRIAGE.md` (human-readable) and `triage.json` (for tooling).

## Real scanners

```bash
npm audit --json > npm.json
python triage.py --input npm.json
```

```bash
pip-audit --format json > pip.json
python triage.py --input pip.json
```

```bash
osv-scanner --format json -r ./repo > osv.json
python triage.py --input osv.json
```

## Flags

- `--reachable <file>` — text file with one package per line; matching findings get a +2 score boost.
- `--prod-only` — push dev-only findings down (not removed).

Stdlib only.
