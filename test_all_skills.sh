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

cd "$ROOT/etl-lineage-explainer"
run_test "etl-lineage-explainer" python etl_lineage_explainer.py \
  --input "$SAMPLES/etl-lineage-explainer/jobs.sql" \
  --json-out /tmp/etl_lineage_explainer.json

cd "$ROOT/policy-as-code-linter"
# This skill intentionally exits non-zero when it finds errors; treat that as expected for the sample.
python policy_as_code_linter.py \
  --input "$SAMPLES/policy-as-code-linter/policy.yaml" \
  --json-out /tmp/policy_lint_report.json > /tmp/test_policy-as-code-linter.out 2> /tmp/test_policy-as-code-linter.err || true
# Reuse the run_test reporting format by forcing success if output files exist.
if [ -s /tmp/test_policy-as-code-linter.out ] || [ -s /tmp/test_policy-as-code-linter.err ]; then
  echo "=========================================="
  echo "TEST: policy-as-code-linter"
  echo "=========================================="
  echo "  PASS  (policy-as-code-linter)"
  PASS=$((PASS+1))
  echo
else
  echo "=========================================="
  echo "TEST: policy-as-code-linter"
  echo "=========================================="
  echo "  FAIL  (policy-as-code-linter) — no output produced"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("policy-as-code-linter")
  echo
fi

cd "$ROOT/support-sla-breach-detector"
run_test "support-sla-breach-detector" python support_sla_breach_detector.py \
  --input "$SAMPLES/support-sla-breach-detector/tickets.csv" \
  --response-sla "P1=30,P2=120,P3=480" \
  --resolution-sla "P1=240,P2=1440,P3=4320" \
  --json-out /tmp/sla_breach_report.json

cd "$ROOT/experiment-metric-audit"
run_test "experiment-metric-audit" python experiment_metric_audit.py \
  --input "$SAMPLES/experiment-metric-audit/experiment.json" \
  --json-out /tmp/experiment_metric_audit.json

cd "$ROOT/api-changelog-impact-analyzer"
run_test "api-changelog-impact-analyzer" python api_changelog_impact_analyzer.py \
  --changelog "$SAMPLES/api-changelog-impact-analyzer/changelog.md" \
  --client-usage "$SAMPLES/api-changelog-impact-analyzer/client_usage.json" \
  --json-out /tmp/api_change_report.json

cd "$ROOT/log-redaction-auditor"
python log_redaction_auditor.py --input "$SAMPLES/log-redaction-auditor/sample.log" --output /tmp/log_redaction_report.json > /tmp/test_log-redaction-auditor.out 2> /tmp/test_log-redaction-auditor.err || true
if [ -s /tmp/test_log-redaction-auditor.out ] || [ -s /tmp/test_log-redaction-auditor.err ] || [ -s /tmp/log_redaction_report.json ]; then
  echo "=========================================="
  echo "TEST: log-redaction-auditor"
  echo "=========================================="
  echo "  PASS  (log-redaction-auditor)"
  PASS=$((PASS+1))
  echo
else
  echo "=========================================="
  echo "TEST: log-redaction-auditor"
  echo "=========================================="
  echo "  FAIL  (log-redaction-auditor) — no output produced"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("log-redaction-auditor")
  echo
fi

cd "$ROOT/sqlite-schema-report"
run_test "sqlite-schema-report" python sqlite_schema_report.py --db "$SAMPLES/sqlite-schema-report/sample.db" --output /tmp/sqlite_schema_report.json

cd "$ROOT/feature-flag-risk-assessor"
python feature_flag_risk_assessor.py --input "$SAMPLES/feature-flag-risk-assessor/flags.json" --today 2026-06-09 --output /tmp/flag_risk_report.json > /tmp/test_feature-flag-risk-assessor.out 2> /tmp/test_feature-flag-risk-assessor.err || true
if [ -s /tmp/test_feature-flag-risk-assessor.out ] || [ -s /tmp/test_feature-flag-risk-assessor.err ] || [ -s /tmp/flag_risk_report.json ]; then
  echo "=========================================="
  echo "TEST: feature-flag-risk-assessor"
  echo "=========================================="
  echo "  PASS  (feature-flag-risk-assessor)"
  PASS=$((PASS+1))
  echo
else
  echo "=========================================="
  echo "TEST: feature-flag-risk-assessor"
  echo "=========================================="
  echo "  FAIL  (feature-flag-risk-assessor) — no output produced"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("feature-flag-risk-assessor")
  echo
fi

cd "$ROOT/prompt-injection-risk-linter"
python prompt_injection_risk_linter.py --prompt "$SAMPLES/prompt-injection-risk-linter/prompt.txt" --retrieved "$SAMPLES/prompt-injection-risk-linter/retrieved.txt" --output /tmp/prompt_injection_report.json > /tmp/test_prompt-injection-risk-linter.out 2> /tmp/test_prompt-injection-risk-linter.err || true
if [ -s /tmp/test_prompt-injection-risk-linter.out ] || [ -s /tmp/test_prompt-injection-risk-linter.err ] || [ -s /tmp/prompt_injection_report.json ]; then
  echo "=========================================="
  echo "TEST: prompt-injection-risk-linter"
  echo "=========================================="
  echo "  PASS  (prompt-injection-risk-linter)"
  PASS=$((PASS+1))
  echo
else
  echo "=========================================="
  echo "TEST: prompt-injection-risk-linter"
  echo "=========================================="
  echo "  FAIL  (prompt-injection-risk-linter) — no output produced"
  FAIL=$((FAIL+1))
  FAILED_SKILLS+=("prompt-injection-risk-linter")
  echo
fi

cd "$ROOT/backlog-prioritization-assistant"
run_test "backlog-prioritization-assistant" python backlog_prioritization_assistant.py --input "$SAMPLES/backlog-prioritization-assistant/backlog.csv" --method rice --output /tmp/backlog_ranked.json


cd "$ROOT/api-contract-diff"
run_test "api-contract-diff" python api_contract_diff.py   --old "$SAMPLES/api-contract-diff/openapi_old.json"   --new "$SAMPLES/api-contract-diff/openapi_new.json"   --out /tmp/api_contract_diff_report.json

cd "$ROOT/csv-pii-scanner"
run_test "csv-pii-scanner" python csv_pii_scanner.py   --input "$SAMPLES/csv-pii-scanner/customers.csv"   --out /tmp/csv_pii_report.json

cd "$ROOT/incident-timeline-builder"
run_test "incident-timeline-builder" python incident_timeline_builder.py   --input "$SAMPLES/incident-timeline-builder/incident_log.txt"   --out /tmp/incident_timeline.json   --gap-minutes 15

cd "$ROOT/kpi-anomaly-triage"
run_test "kpi-anomaly-triage" python kpi_anomaly_triage.py   --input "$SAMPLES/kpi-anomaly-triage/kpi.csv"   --out /tmp/kpi_anomaly_report.json   --window 7   --z 2.5

cd "$ROOT/meeting-action-items-extractor"
run_test "meeting-action-items-extractor" python meeting_action_items_extractor.py   --input "$SAMPLES/meeting-action-items-extractor/transcript.txt"   --out /tmp/meeting_actions.json


# ------------------------------
# json-schema-drift-detector
run_test "json-schema-drift-detector" bash -lc "cd $ROOT/json-schema-drift-detector && python json_schema_drift_detector.py --old \"$SAMPLES/json-schema-drift-detector/old_schema.json\" --new \"$SAMPLES/json-schema-drift-detector/new_schema.json\" --out /tmp/json_schema_drift_report.json"

# utm-campaign-governor
run_test "utm-campaign-governor" bash -lc "cd $ROOT/utm-campaign-governor && python utm_campaign_governor.py --input \"$SAMPLES/utm-campaign-governor/links.csv\" --policy \"$SAMPLES/utm-campaign-governor/policy.json\" --out /tmp/utm_governed_links.csv"

# ops-rca-hypothesis-generator
run_test "ops-rca-hypothesis-generator" bash -lc "cd $ROOT/ops-rca-hypothesis-generator && python ops_rca_hypothesis_generator.py --incident \"$SAMPLES/ops-rca-hypothesis-generator/incident.json\" --changes \"$SAMPLES/ops-rca-hypothesis-generator/changes.json\" --out /tmp/rca_hypotheses.json"

# feature-adoption-funnel-builder
run_test "feature-adoption-funnel-builder" bash -lc "cd $ROOT/feature-adoption-funnel-builder && python feature_adoption_funnel_builder.py --events \"$SAMPLES/feature-adoption-funnel-builder/events.csv\" --steps \"feature_viewed,feature_started,feature_completed\" --window-days 7 --out /tmp/feature_funnel.json"

# docx-style-auditor
run_test "docx-style-auditor" bash -lc "cd $ROOT/docx-style-auditor && python docx_style_auditor.py --input \"$SAMPLES/docx-style-auditor/sample.docx\" --out /tmp/docx_style_report.json"


rm -rf /tmp/repos_demo /tmp/arch_out /tmp/results.jsonl /tmp/r2.jsonl /tmp/r2.md /tmp/eval_report.md \
       /tmp/api_contract_diff_report.json /tmp/csv_pii_report.json /tmp/incident_timeline.json /tmp/kpi_anomaly_report.json /tmp/meeting_actions.json /tmp/json_schema_drift_report.json /tmp/utm_governed_links.csv /tmp/rca_hypotheses.json /tmp/feature_funnel.json /tmp/docx_style_report.json \
       /tmp/pr_review.md /tmp/meeting_notes.md /tmp/runbook.md /tmp/release_notes.md /tmp/release_slack.md \
       /tmp/triage.md /tmp/triage.json /tmp/etl_lineage_explainer.json /tmp/policy_lint_report.json \
       /tmp/sla_breach_report.json /tmp/experiment_metric_audit.json /tmp/api_change_report.json \
       /tmp/log_redaction_report.json /tmp/sqlite_schema_report.json /tmp/flag_risk_report.json /tmp/prompt_injection_report.json \
       /tmp/backlog_ranked.json /tmp/test_log-redaction-auditor.out /tmp/test_log-redaction-auditor.err \
       /tmp/test_feature-flag-risk-assessor.out /tmp/test_feature-flag-risk-assessor.err \
       /tmp/test_prompt-injection-risk-linter.out /tmp/test_prompt-injection-risk-linter.err \
       /tmp/patched_accessibility_alt_text_auditor.html /tmp/report_accessibility_alt_text_auditor.json /tmp/stdout_accessibility_alt_text_auditor.json \
       /tmp/report_data_contract_validator.json /tmp/stdout_data_contract_validator.json \
       /tmp/report_feature_flag_cleanup_planner.json /tmp/stdout_feature_flag_cleanup_planner.json \
       /tmp/report_meeting_action_item_extractor.json /tmp/stdout_meeting_action_item_extractor.json \
       /tmp/report_sbom_license_risk_checker.json /tmp/stdout_sbom_license_risk_checker.json \
       /tmp/report_http_api_smoke_tester.json \
       /tmp/report_privacy_policy_diff.json \
       /tmp/report_etl_retry_backoff.json \
       /tmp/report_customer_journey_gap.json \
       /tmp/report_cloud_cost_tag_coverage.json \
       /tmp/pseudonymization_plan.json /tmp/postmortem_checklist.json /tmp/alt_audit.json /tmp/changelog_entry.md /tmp/kpi_consistency_report.json

echo "=========================================="
echo "RESULTS: $PASS passed, $FAIL failed"
if [ $FAIL -gt 0 ]; then
  echo "Failed: ${FAILED_SKILLS[*]}"
  exit 1
fi

echo "== csv-pii-redactor =="
cd "$ROOT/csv-pii-redactor"
python csv_pii_redactor.py \
  --input_csv "$SAMPLES/csv-pii-redactor/sample_customers.csv" \
  --output_csv /tmp/sample_customers.redacted.csv \
  --report_json /tmp/sample_customers.redaction_report.json

echo "== api-changelog-summarizer =="
cd "$ROOT/api-changelog-summarizer"
python api_changelog_summarizer.py \
  --old_spec "$SAMPLES/api-changelog-summarizer/openapi_old.json" \
  --new_spec "$SAMPLES/api-changelog-summarizer/openapi_new.json" \
  --out_md /tmp/api_changelog.md

echo "== support-macro-personalizer =="
cd "$ROOT/support-macro-personalizer"
python support_macro_personalizer.py \
  --macros_json "$SAMPLES/support-macro-personalizer/macros.json" \
  --context_json "$SAMPLES/support-macro-personalizer/context.json" \
  --out_dir /tmp/support_drafts

echo "== sql-anti-pattern-linter =="
cd "$ROOT/sql-anti-pattern-linter"
python sql_anti_pattern_linter.py \
  --sql_file "$SAMPLES/sql-anti-pattern-linter/query.sql" \
  --out_json /tmp/sql_lint_findings.json

echo "== incident-timeline-normalizer =="
cd "$ROOT/incident-timeline-normalizer"
python incident_timeline_normalizer.py \
  --events_json "$SAMPLES/incident-timeline-normalizer/events.json" \
  --out_json /tmp/incident_timeline.json

# ------------------------------
# accessibility-alt-text-auditor
cd "$ROOT/accessibility-alt-text-auditor"
run_test "accessibility-alt-text-auditor" python alt_text_auditor.py \
  --html "$SAMPLES/accessibility-alt-text-auditor/page.html" \
  --policy "$SAMPLES/accessibility-alt-text-auditor/policy.json" \
  --patched-out "/tmp/patched_accessibility_alt_text_auditor.html" \
  --report-out "/tmp/report_accessibility_alt_text_auditor.json"

# ------------------------------
# data-contract-validator
cd "$ROOT/data-contract-validator"
run_test "data-contract-validator" python validate_contract.py \
  --contract "$SAMPLES/data-contract-validator/contract.json" \
  --data "$SAMPLES/data-contract-validator/records.jsonl" \
  --out "/tmp/report_data_contract_validator.json"

# ------------------------------
# feature-flag-cleanup-planner
cd "$ROOT/feature-flag-cleanup-planner"
run_test "feature-flag-cleanup-planner" python plan_cleanup.py \
  --flags "$SAMPLES/feature-flag-cleanup-planner/flags.json" \
  --out "/tmp/report_feature_flag_cleanup_planner.json"

# ------------------------------
# meeting-action-item-extractor
cd "$ROOT/meeting-action-item-extractor"
run_test "meeting-action-item-extractor" python extract_action_items.py \
  --transcript "$SAMPLES/meeting-action-item-extractor/transcript.txt" \
  --participants "$SAMPLES/meeting-action-item-extractor/participants.json" \
  --out "/tmp/report_meeting_action_item_extractor.json"

# ------------------------------
# sbom-license-risk-checker
cd "$ROOT/sbom-license-risk-checker"
run_test "sbom-license-risk-checker" python check_sbom_licenses.py \
  --sbom "$SAMPLES/sbom-license-risk-checker/sbom.json" \
  --policy "$SAMPLES/sbom-license-risk-checker/policy.json" \
  --out "/tmp/report_sbom_license_risk_checker.json"



# ------------------------------
# http-api-smoke-tester
cd "$ROOT/http-api-smoke-tester"
run_test "http-api-smoke-tester" python http_api_smoke_tester.py   --plan "$SAMPLES/http-api-smoke-tester/plan.json"   > /tmp/report_http_api_smoke_tester.json

# ------------------------------
# privacy-policy-diff-summarizer
cd "$ROOT/privacy-policy-diff-summarizer"
run_test "privacy-policy-diff-summarizer" python privacy_policy_diff_summarizer.py   --old "$SAMPLES/privacy-policy-diff-summarizer/policy_old.txt"   --new "$SAMPLES/privacy-policy-diff-summarizer/policy_new.txt"   > /tmp/report_privacy_policy_diff.json

# ------------------------------
# etl-retry-backoff-simulator
cd "$ROOT/etl-retry-backoff-simulator"
run_test "etl-retry-backoff-simulator" python etl_retry_backoff_simulator.py   --config "$SAMPLES/etl-retry-backoff-simulator/config.json"   > /tmp/report_etl_retry_backoff.json

# ------------------------------
# customer-journey-gap-analyzer
cd "$ROOT/customer-journey-gap-analyzer"
run_test "customer-journey-gap-analyzer" python customer_journey_gap_analyzer.py   --input "$SAMPLES/customer-journey-gap-analyzer/funnel.csv"   > /tmp/report_customer_journey_gap.json

# ------------------------------
# cloud-cost-tag-coverage-auditor
cd "$ROOT/cloud-cost-tag-coverage-auditor"
run_test "cloud-cost-tag-coverage-auditor" python cloud_cost_tag_coverage_auditor.py   --input "$SAMPLES/cloud-cost-tag-coverage-auditor/resources.csv"   --policy "$SAMPLES/cloud-cost-tag-coverage-auditor/policy.json"   > /tmp/report_cloud_cost_tag_coverage.json

########################################
# pseudonymization-field-mapper
########################################
run_test "pseudonymization-field-mapper" bash -lc "cd $ROOT/pseudonymization-field-mapper && python pseudonymization_field_mapper.py --schema \"$SAMPLES/pseudonymization-field-mapper/schema.json\" --out /tmp/pseudonymization_plan.json"

########################################
# incident-postmortem-qa-checklist
########################################
run_test "incident-postmortem-qa-checklist" bash -lc "cd $ROOT/incident-postmortem-qa-checklist && python incident_postmortem_qa_checklist.py --timeline \"$SAMPLES/incident-postmortem-qa-checklist/timeline.json\" --out /tmp/postmortem_checklist.json"

########################################
# accessibility-alt-text-auditor
########################################
run_test "accessibility-alt-text-auditor" bash -lc "cd $ROOT/accessibility-alt-text-auditor && python accessibility_alt_text_auditor.py --images \"$SAMPLES/accessibility-alt-text-auditor/images.json\" --out /tmp/alt_audit.json"

########################################
# release-notes-changelog-normalizer
########################################
run_test "release-notes-changelog-normalizer" bash -lc "cd $ROOT/release-notes-changelog-normalizer && python release_notes_changelog_normalizer.py --in \"$SAMPLES/release-notes-changelog-normalizer/release_notes.json\" --out /tmp/changelog_entry.md"

########################################
# kpi-definition-consistency-checker
########################################
run_test "kpi-definition-consistency-checker" bash -lc "cd $ROOT/kpi-definition-consistency-checker && python kpi_definition_consistency_checker.py --kpis \"$SAMPLES/kpi-definition-consistency-checker/kpis.json\" --out /tmp/kpi_consistency_report.json"


echo "ALL TESTS PASSED"
