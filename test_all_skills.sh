#!/usr/bin/env bash
# Comprehensive test runner for every skill in skills/.
# Exits 0 only if every skill passes.
set -u
REPO="$(cd "$(dirname "$0")" && pwd)"
ROOT="$REPO/skills"
SAMPLES="$REPO/samples"
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

cd "$ROOT/product-analytics-investigator"
run_test "product-analytics" python investigate.py \
  --source csv --csv "$SAMPLES/product-analytics-investigator/sample_events.csv" \
  --steps view_pricing start_checkout purchase \
  --segment platform --current-days 7 --prior-days 7 \
  --end 2026-05-07T00:00:00Z

cd "$ROOT/growth-experiment-planner"
run_test "growth-experiment-prop" python plan.py \
  --metric-type proportion --baseline 0.12 --mde 0.05 \
  --daily-users 20000 --variants 2

run_test "growth-experiment-mean" python plan.py \
  --metric-type mean --baseline 4.20 --stddev 2.10 --mde 0.03 \
  --daily-users 8000 --variants 2

cd "$ROOT/crm-opportunity-summarizer"
run_test "crm-summarizer" python summarize.py --source csv --csv "$SAMPLES/crm-opportunity-summarizer/sample/opportunities.csv"

cd "$ROOT/customer-interview-analyzer"
run_test "interview-analyzer" python analyze.py --dir "$SAMPLES/customer-interview-analyzer/sample_transcripts" --question "Why is onboarding hard?"

cd "$ROOT/incident-postmortem-builder"
run_test "postmortem" python build.py \
  --incident-id INC-1234 --title "Checkout 5xx surge" --severity Sev2 \
  --started 2026-05-03T13:55:00Z \
  --detected 2026-05-03T14:02:00Z \
  --mitigated 2026-05-03T14:31:00Z \
  --resolved 2026-05-03T15:10:00Z \
  --timeline "$SAMPLES/incident-postmortem-builder/sample_timeline.csv" \
  --impact-users 12000 --impact-revenue 4200

cd "$ROOT/data-contract-enforcer"
run_test "data-contract" python enforce.py --contract "$SAMPLES/data-contract-enforcer/contracts/fct_orders.yml" --seed

cd "$ROOT/saas-spend-optimizer"
run_test "saas-spend" python optimize.py --subs "$SAMPLES/saas-spend-optimizer/sample/subscriptions.csv" --usage "$SAMPLES/saas-spend-optimizer/sample/usage.csv"

cd "$ROOT/regulatory-guardrail-checker"
run_test "guardrail" python check.py --spec "$SAMPLES/regulatory-guardrail-checker/sample_spec.md" --regimes gdpr,ccpa,soc2,wcag

if grep -q "GDPR" "/tmp/test_guardrail.out" && grep -q "Automated decision-making" "/tmp/test_guardrail.out"; then
  echo "  PASS  (guardrail-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (guardrail-content-check) — expected risks not found"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("guardrail-content-check")
fi
echo

mkdir -p /tmp/repos_demo/svc-a /tmp/repos_demo/svc-b
echo '{}' > /tmp/repos_demo/svc-a/package.json
echo '{"dependencies":{"express":"^4"}}' > /tmp/repos_demo/svc-b/package.json
echo "fetch('http://svc-a/api')" > /tmp/repos_demo/svc-b/index.js
echo "console.log('hi')" > /tmp/repos_demo/svc-a/index.js
cd "$ROOT/architecture-map-builder"
run_test "arch-map" python map.py --path /tmp/repos_demo --out /tmp/arch_out

if grep -q "svc_b --> svc_a" /tmp/arch_out/architecture.mmd; then
  echo "  PASS  (arch-map-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (arch-map-content-check) — dependency edge missing"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("arch-map-content-check")
fi
echo

cd "$ROOT/ai-eval-regression-tester"
run_test "eval-tester" python run_eval.py \
  --suite "$SAMPLES/ai-eval-regression-tester/suite.yml" --runner runners:echo \
  --threshold 0.9 --out /tmp/results.jsonl --report /tmp/eval_report.md

if grep -q "Pass rate:.*100" "/tmp/test_eval-tester.out"; then
  echo "  PASS  (eval-tester-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (eval-tester-content-check) — pass rate not 100%"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("eval-tester-content-check")
fi
echo

cd "$ROOT/ai-eval-regression-tester"
if python run_eval.py --suite "$SAMPLES/ai-eval-regression-tester/suite.yml" --runner runners:echo \
   --threshold 1.01 --out /tmp/r2.jsonl --report /tmp/r2.md > /dev/null 2>&1; then
  echo "  FAIL  (eval-tester-gating) — should have exited non-zero"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("eval-tester-gating")
else
  echo "  PASS  (eval-tester-gating)"
  PASS=$((PASS+1))
fi
echo

cd "$ROOT/pr-review-summarizer"
run_test "pr-review-summarizer" python review.py --diff "$SAMPLES/pr-review-summarizer/sample.diff" --out /tmp/pr_review.md

if grep -q "Pull Request Review Brief" /tmp/pr_review.md && grep -q "security-sensitive" /tmp/pr_review.md; then
  echo "  PASS  (pr-review-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (pr-review-content-check) — expected sections missing"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("pr-review-content-check")
fi
echo

cd "$ROOT/meeting-notes-distiller"
run_test "meeting-notes-distiller" python distill.py \
  --in "$SAMPLES/meeting-notes-distiller/sample_transcript.txt" --attendees "Alice,Bob,Carol" --purpose "Q3 planning" \
  --out /tmp/meeting_notes.md

if grep -q "Action items" /tmp/meeting_notes.md && grep -q "Decisions" /tmp/meeting_notes.md; then
  echo "  PASS  (meeting-notes-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (meeting-notes-content-check) — expected sections missing"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("meeting-notes-content-check")
fi
echo

cd "$ROOT/oncall-runbook-executor"
run_test "oncall-runbook-dry-run" python runbook.py --runbook "$SAMPLES/oncall-runbook-executor/sample_runbook.yml" --yes --log /tmp/runbook.md

if grep -q "dry-run" /tmp/runbook.md && grep -q "print_uptime" /tmp/runbook.md; then
  echo "  PASS  (oncall-runbook-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (oncall-runbook-content-check) — expected steps missing"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("oncall-runbook-content-check")
fi
echo

cd "$ROOT/release-notes-writer"
run_test "release-notes-writer" python generate.py \
  --prs "$SAMPLES/release-notes-writer/sample_prs.csv" --version 3.2.0 --date 2026-05-07 \
  --out-md /tmp/release_notes.md --out-slack /tmp/release_slack.md

if grep -q "Breaking changes" /tmp/release_notes.md && grep -q "New features" /tmp/release_notes.md && grep -q "Bug fixes" /tmp/release_notes.md; then
  echo "  PASS  (release-notes-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (release-notes-content-check) — expected sections missing"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("release-notes-content-check")
fi
echo

cd "$ROOT/dependency-vuln-triager"
run_test "dependency-vuln-triager" python triage.py \
  --input "$SAMPLES/dependency-vuln-triager/sample_audit.json" --reachable "$SAMPLES/dependency-vuln-triager/sample_reachable.txt" --prod-only \
  --out-md /tmp/triage.md --out-json /tmp/triage.json

if grep -q "P0" /tmp/triage.md && grep -q "axios" /tmp/triage.md && grep -q "reachable" /tmp/triage.md; then
  echo "  PASS  (vuln-triage-content-check)"
  PASS=$((PASS+1))
else
  echo "  FAIL  (vuln-triage-content-check) — expected groupings missing"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("vuln-triage-content-check")
fi
echo

rm -rf /tmp/repos_demo /tmp/arch_out /tmp/results.jsonl /tmp/r2.jsonl /tmp/r2.md /tmp/eval_report.md \
       /tmp/pr_review.md /tmp/meeting_notes.md /tmp/runbook.md /tmp/release_notes.md /tmp/release_slack.md \
       /tmp/triage.md /tmp/triage.json

echo "=========================================="
echo "RESULTS: $PASS passed, $FAIL failed"
if [ $FAIL -gt 0 ]; then
  echo "Failed: ${FAILED_SKILLS[*]}"
  exit 1
fi
echo "ALL TESTS PASSED"
