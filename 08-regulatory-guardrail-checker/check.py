"""Regulatory Guardrail Checker.

Scans a spec / PRD for compliance signals and produces a risk register plus
a required-controls checklist.

Usage:
  python check.py --spec spec.md --regimes gdpr,ccpa,hipaa,pci,soc2,wcag
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SIGNALS = {
    "pii": [r"\b(email|phone|address|name|date of birth|dob|ip address)\b"],
    "phi": [r"\b(health|medical|diagnosis|prescription|patient|hipaa|phi|ehr)\b"],
    "payment": [r"\b(credit card|cvv|pan|payment|stripe|braintree|pci)\b"],
    "biometric": [r"\b(fingerprint|face id|iris|biometric|voice id)\b"],
    "minors": [r"\b(under 13|minor|coppa|teen)\b"],
    "location": [r"\b(geolocation|gps|precise location|geo-?fence)\b"],
    "third_party_sharing": [r"\b(share with|send to|export to|integrat(e|ion))\b"],
    "automated_decision": [r"\b(auto[- ]?approv(e|al)|automated decision|risk score|model score|ai (decision|recommendation))\b"],
    "marketing": [r"\b(marketing|promotional|email blast|push notification)\b"],
    "retention": [r"\b(retention|store for|keep for|delete after)\b"],
    "consent": [r"\b(consent|opt[- ]?in|opt[- ]?out|do not sell|preference center)\b"],
    "logging": [r"\b(audit log|access log|event log)\b"],
    "encryption": [r"\b(encrypt(ion|ed)?|tls|kms|at rest|in transit)\b"],
    "user_dsr": [r"\b(data subject|access request|right to (erasure|delete|portability)|dsar|delete my data)\b"],
    "accessibility": [r"\b(screen reader|aria|alt text|keyboard navigation|contrast ratio|wcag)\b"],
}


@dataclass
class RiskItem:
    regime: str
    risk: str
    severity: str  # High | Medium | Low
    control: str
    owner: str


def extract_signals(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    low = text.lower()
    for sig, patterns in SIGNALS.items():
        hits: list[str] = []
        for p in patterns:
            for m in re.finditer(p, low):
                hits.append(m.group(0))
        if hits:
            found[sig] = list(dict.fromkeys(hits))[:5]
    return found


def assess(signals: dict[str, list[str]], regimes: set[str]) -> tuple[list[RiskItem], list[str], list[str]]:
    risks: list[RiskItem] = []
    controls: list[str] = []
    open_q: list[str] = []

    has_pii = "pii" in signals
    has_phi = "phi" in signals
    has_payment = "payment" in signals
    has_minors = "minors" in signals
    has_marketing = "marketing" in signals
    has_third = "third_party_sharing" in signals
    has_auto = "automated_decision" in signals
    has_loc = "location" in signals
    has_consent = "consent" in signals
    has_dsr = "user_dsr" in signals
    has_logging = "logging" in signals
    has_enc = "encryption" in signals
    has_retention = "retention" in signals
    has_a11y = "accessibility" in signals

    if "gdpr" in regimes and has_pii:
        sev = "High" if has_third or has_marketing or has_auto else "Medium"
        risks.append(RiskItem("GDPR", "Processing of personal data", sev,
                              "Document lawful basis (Art. 6); record of processing (Art. 30); DPIA if high-risk",
                              "privacy-counsel"))
        if not has_consent:
            open_q.append("GDPR: confirm lawful basis and whether consent UI is needed.")
        if not has_dsr:
            controls.append("Implement DSR endpoints (access, rectification, erasure, portability) and SLA tracking.")
        if has_auto:
            risks.append(RiskItem("GDPR", "Automated decision-making (Art. 22)", "High",
                                  "Provide meaningful information about logic, allow human review, contest mechanism",
                                  "product+legal"))
    if "ccpa" in regimes and has_pii:
        risks.append(RiskItem("CCPA/CPRA", "Personal information collection", "Medium",
                              "Update privacy notice, provide Do Not Sell/Share, honor GPC signal",
                              "privacy-counsel"))
    if "hipaa" in regimes and has_phi:
        risks.append(RiskItem("HIPAA", "PHI processing", "High",
                              "Sign BAAs with subprocessors; encryption in transit + at rest; audit logging; minimum necessary",
                              "security+legal"))
        if not has_logging:
            controls.append("Enable immutable audit logging covering all PHI access events.")
        if not has_enc:
            controls.append("Confirm AES-256 at rest and TLS1.2+ in transit for PHI stores and flows.")
    if "pci" in regimes and has_payment:
        risks.append(RiskItem("PCI-DSS", "Cardholder data in scope", "High",
                              "Tokenize via PSP (Stripe/Adyen); never store PAN; enforce SAQ-A scope",
                              "security+payments-eng"))
    if "soc2" in regimes:
        if not has_logging:
            controls.append("SOC2 CC7: ensure detection logs and incident response are wired up before launch.")
        if has_pii and not has_enc:
            controls.append("SOC2 CC6: confirm encryption controls and key management for the new data flows.")
    if has_minors:
        risks.append(RiskItem("COPPA / age", "Possible processing of minors' data", "High",
                              "Age gate, verifiable parental consent if <13, restrict marketing/profile",
                              "privacy-counsel"))
    if has_loc and not has_consent:
        open_q.append("Location data without explicit consent flow — confirm opt-in UX.")
    if has_marketing and not has_consent:
        controls.append("Add opt-in for marketing comms and unsubscribe link in every send.")
    if has_third:
        controls.append("List subprocessors in DPA/sub-processor page; ensure DPAs in place.")
    if has_retention is False:
        open_q.append("No retention period detected — confirm data minimization and deletion schedule.")
    if "wcag" in regimes:
        if not has_a11y:
            controls.append("Run a WCAG 2.2 AA review (color contrast, keyboard nav, ARIA, focus order, screen reader).")
        risks.append(RiskItem("WCAG 2.2 AA", "Accessibility coverage", "Medium",
                              "Manual + automated a11y audit; remediate before launch",
                              "design+frontend"))

    return risks, controls, open_q


def render(signals, risks, controls, open_q) -> str:
    lines = ["# Compliance Pre-Launch Review", "", "## Detected signals"]
    if not signals:
        lines.append("- (none detected — verify spec coverage)")
    for k, v in signals.items():
        lines.append(f"- **{k}** — examples: {', '.join(v)}")

    lines += ["", "## Risk register",
              "| Regime | Risk | Severity | Required control | Owner |",
              "|---|---|---|---|---|"]
    for r in risks:
        lines.append(f"| {r.regime} | {r.risk} | {r.severity} | {r.control} | {r.owner} |")
    if not risks:
        lines.append("| — | — | — | — | — |")

    lines += ["", "## Required controls checklist"]
    for c in controls:
        lines.append(f"- [ ] {c}")
    if not controls:
        lines.append("- [ ] (none auto-generated — manual review still required)")

    lines += ["", "## Open questions for legal/security"]
    for q in open_q:
        lines.append(f"- {q}")
    if not open_q:
        lines.append("- (none)")
    lines += ["", "_Auto-generated; not legal advice. Confirm with privacy counsel and security before launch._"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", required=True, help="Path to PRD/spec, or - for stdin")
    ap.add_argument("--regimes", default="gdpr,ccpa,soc2,wcag",
                    help="Comma-separated: gdpr,ccpa,hipaa,pci,soc2,wcag")
    ap.add_argument("--out", default="-")
    args = ap.parse_args()

    text = sys.stdin.read() if args.spec == "-" else Path(args.spec).read_text(errors="ignore")
    regimes = {r.strip().lower() for r in args.regimes.split(",") if r.strip()}
    signals = extract_signals(text)
    risks, controls, open_q = assess(signals, regimes)
    body = render(signals, risks, controls, open_q)
    if args.out == "-":
        print(body)
    else:
        Path(args.out).write_text(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
