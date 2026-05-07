# data-contract-enforcer

Validate a warehouse table against a YAML data contract. Exits non-zero on violations — drop into CI.

## Run (demo with DuckDB)

```bash
pip install -r requirements.txt
python enforce.py --contract contracts/fct_orders.yml --seed
```

For a real warehouse:

```bash
python enforce.py --contract contracts/fct_orders.yml \
  --dsn 'snowflake://user:pass@account/db/schema?warehouse=WH'
```

See [SKILL.md](./SKILL.md).
