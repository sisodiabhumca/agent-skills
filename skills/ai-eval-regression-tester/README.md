# ai-eval-regression-tester

Run a regression eval suite against an LLM app. CI-friendly (exits non-zero on failure).

## Run (demo)

```bash
python run_eval.py --suite ../../samples/ai-eval-regression-tester/suite.yml --runner runners:echo --threshold 0.9
```

For your app, write a runner that calls your model:

```python
# runners.py
def my_app(case_input: str) -> str:
    return openai_call(...)
```

```bash
python run_eval.py --suite ../../samples/ai-eval-regression-tester/suite.yml --runner runners:my_app \
  --baseline last_run.jsonl --threshold 0.95 --tag-threshold refund=0.98
```

See [SKILL.md](./SKILL.md).

## Sample data

Sample inputs for this skill live in `../../samples/ai-eval-regression-tester/` (kept outside the skill folder so security scanners don't need to handle non-code data).
