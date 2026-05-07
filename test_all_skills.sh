#!/usr/bin/env bash
# Comprehensive test runner for all 10 skills.
# Exits 0 only if every skill passes.
set -u
ROOT="/home/user/workspace/agent-skills"
PASS=0
FAIL=0
FAILED_SKILLS=()

run_test() {
  local name="$1"
  shift
  echo "=========================================="
  echo "TEST: $name"
  echo "=========================================="
  if "$@" > "/tmp/test_${name}.out" 2> "/tmp/test_${name}.err"; then
    echo "  PASS  ($name)"
    PASS=$((PASS+1))
  else
    echo "  FAIL  ($name) — exit=$?"
    echo "  --- stdout (last 20) ---"
    tail -20 "/tmp/test_${name}.out"
    echo "  --- stderr (last 20) ---"
    tail -20 "/tmp/test_${name}.err"
    FAIL=$((FAIL+1))
    FAILED_SKILLS+=("$name")
  fi
  echo
}

# 1. product-analytics-investigator
cd "$ROOT/01-product-analytics-investigator"
run_test "01-product-analytics" python investigate.py \
  --source csv --csv sample_events.csv \
  --steps view_pricing start_checkout purchase \
  --segment platform --current-days 7 --prior-days 7 \
  --end 2026-05-07T00:00:00Z

# 2. growth-experiment-planner — proportion
cd "$ROOT/02-growth-experiment-planner"
run_test "02-growth-experiment-prop" python plan.py \
  --metric-type proportion --baseline 0.12 --mde 0.05 \
  --daily-users 20000 --variants 2

# 2b. growth-experiment-planner — mean
run_test "02-growth-experiment-mean" python plan.py \
  --metric-type mean --baseline 4.20 --stddev 2.10 --mde 0.03 \
  --daily-users 8000 --variants 2

# 3. crm-opportunity-summarizer
cd "$ROOT/03-crm-opportunity-summarizer"
run_test "03-crm-summarizer" python summarize.py --source csv --csv sample/opportunities.csv

# 4. customer-interview-analyzer
cd "$ROOT/04-customer-interview-analyzer"
run_test "04-interview-analyzer" python analyze.py --dir sample_transcripts --question "Why is onboarding hard?"

# 5. incident-postmortem-builder
cd "$ROOT/05-incident-postmortem-builder"
run_test "05-postmortem" python build.py \
  --incident-id INC-1234 --title "Checkout 5xx surge" --severity Sev2 \
  --started 2026-05-03T13:55:00Z \
  --detected 2026-05-03T14:02:00Z \
  --mitigated 2026-05-03T14:31:00Z \
  --resolved 2026-05-03T15:10:00Z \
  --timeline sample_timeline.csv \
  --impact-users 12000 --impact-revenue 4200

# 6. data-contract-enforcer (DuckDB demo)
cd "$ROOT/06-data-contract-enforcer"
run_test "06-data-contract" python enforce.py --contract contracts/fct_orders.yml --seed

# 7. saas-spend-optimizer
cd "$ROOT/07-saas-spend-optimizer"
run_test "07-saas-spend" python optimize.py --subs sample/subscriptions.csv --usage sample/usage.csv

# 8. regulatory-guardrail-checker
cd "$ROOT/08-regulatory-guardrail-checker"
run_test "08-guardrail" python check.py --spec sample_spec.md --regimes gdpr,ccpa,soc2,wcag

# 8b. confirm risks were detected
if grep -q "GDPR" "/tmp/test_08-guardrail.out" && grep -q "Automated decision-making" "/tmp/test_08-guardrail.out"; then
  echo "  PASS  (08-guardrail-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (08-guardrail-content-check) — expected risks not found"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("08-guardrail-content-check")
fi
echo

# 9. architecture-map-builder
mkdir -p /tmp/repos_demo/svc-a /tmp/repos_demo/svc-b
echo '{}' > /tmp/repos_demo/svc-a/package.json
echo '{"dependencies":{"express":"^4"}}' > /tmp/repos_demo/svc-b/package.json
echo "fetch('http://svc-a/api')" > /tmp/repos_demo/svc-b/index.js
echo "console.log('hi')" > /tmp/repos_demo/svc-a/index.js
cd "$ROOT/09-architecture-map-builder"
run_test "09-arch-map" python map.py --path /tmp/repos_demo --out /tmp/arch_out

# 9b. confirm dependency was detected
if grep -q "svc_b --> svc_a" /tmp/arch_out/architecture.mmd; then
  echo "  PASS  (09-arch-map-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (09-arch-map-content-check) — dependency edge missing"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("09-arch-map-content-check")
fi
echo

# 10. ai-eval-regression-tester
cd "$ROOT/10-ai-eval-regression-tester"
run_test "10-eval-tester" python run_eval.py \
  --suite suite.yml --runner runners:echo \
  --threshold 0.9 --out /tmp/results.jsonl --report /tmp/eval_report.md

# 10b. confirm 100% pass rate in echo runner case
if grep -q "Pass rate:.*100" "/tmp/test_10-eval-tester.out"; then
  echo "  PASS  (10-eval-tester-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (10-eval-tester-content-check) — pass rate not 100%"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("10-eval-tester-content-check")
fi
echo

# 10c. exit-code gating: force a fail with a higher threshold
cd "$ROOT/10-ai-eval-regression-tester"
if python run_eval.py --suite suite.yml --runner runners:echo \
   --threshold 1.01 --out /tmp/r2.jsonl --report /tmp/r2.md > /dev/null 2>&1; then
  echo "  FAIL  (10-eval-tester-gating) — should have exited non-zero"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("10-eval-tester-gating")
else
  echo "  PASS  (10-eval-tester-gating)"
  PASS=$((PASS+1))
fi
echo

# Cleanup
rm -rf /tmp/repos_demo /tmp/arch_out /tmp/results.jsonl /tmp/r2.jsonl /tmp/r2.md /tmp/eval_report.md

echo "=========================================="
echo "RESULTS: $PASS passed, $FAIL failed"
if [ $FAIL -gt 0 ]; then
  echo "Failed: ${FAILED_SKILLS[*]}"
  exit 1
fi
echo "ALL TESTS PASSED"
