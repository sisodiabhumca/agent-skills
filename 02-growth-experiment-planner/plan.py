"""Growth Experiment Planner.

Computes sample size + runtime and emits a launch-ready experiment brief.

Examples:
  python plan.py --metric-type proportion --baseline 0.12 --mde 0.05 --daily-users 20000 --variants 2
  python plan.py --metric-type mean --baseline 4.20 --stddev 2.10 --mde 0.03 --daily-users 8000 --variants 2
"""
from __future__ import annotations

import argparse
import math
import sys


def z(p: float) -> float:
    """Inverse normal CDF using Beasley-Springer-Moro (good enough for alpha/beta)."""
    a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2,
         1.383577518672690e2, -3.066479806614716e1, 2.506628277459239]
    b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2,
         6.680131188771972e1, -1.328068155288572e1]
    c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838,
         -2.549732539343734, 4.374664141464968, 2.938163982698783]
    d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996,
         3.754408661907416]
    plow = 0.02425
    phigh = 1 - plow
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1-p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def sample_size_proportion(p1: float, mde_rel: float, alpha: float = 0.05, power: float = 0.8) -> int:
    p2 = p1 * (1 + mde_rel)
    p_bar = (p1 + p2) / 2
    z_alpha = z(1 - alpha / 2)
    z_beta = z(power)
    num = (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) + z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    den = (p2 - p1) ** 2
    return math.ceil(num / den)


def sample_size_mean(mu: float, sigma: float, mde_rel: float, alpha: float = 0.05, power: float = 0.8) -> int:
    delta = mu * mde_rel
    z_alpha = z(1 - alpha / 2)
    z_beta = z(power)
    return math.ceil(2 * ((z_alpha + z_beta) ** 2) * (sigma ** 2) / (delta ** 2))


def render_brief(args, n_per_arm: int, total_n: int, days: float) -> str:
    arms = ["control"] + [f"treatment_{i}" for i in range(1, args.variants)]
    return f"""# Experiment Brief — {args.name or 'Unnamed Test'}

## Hypothesis
{args.hypothesis or '<TBD: state the change, expected effect, and reasoning>'}

## Variants ({args.variants})
{chr(10).join(f"- **{a}** — {int(100/args.variants)}% allocation" for a in arms)}

## Primary metric
- **Name:** {args.metric_name or 'TBD'}
- **Type:** {args.metric_type}
- **Baseline:** {args.baseline}{' (rate)' if args.metric_type == 'proportion' else ''}
- **MDE (relative):** {args.mde*100:.1f}%

## Sample size
- **Per arm:** {n_per_arm:,}
- **Total:** {total_n:,}
- **Daily users on surface:** {args.daily_users:,}
- **Estimated runtime:** **{days:.1f} days** ({math.ceil(days/7)} weeks)
- **Power:** {args.power}, **Alpha:** {args.alpha}

## Guardrails (must NOT regress)
- Error rate (5xx, JS errors)
- p95 latency on affected pages
- Revenue per user
- {args.guardrails or '<add domain-specific guardrails>'}

## Stopping rules
- Stop early ONLY for guardrail breach (>10% relative regression on guardrail with p<0.01).
- Do not peek at primary metric for early-stopping unless using a sequential test.
- Plan to run the full {days:.0f} days even if results trend significant earlier.

## Pre-launch QA checklist
- [ ] Event instrumentation verified in staging
- [ ] Variant assignment is sticky per user
- [ ] Allocation matches plan (chi-square sanity check after 24h)
- [ ] Guardrail dashboards live before launch
- [ ] Holdout and rollback plan documented

## Rollback plan
- Trigger: any guardrail regresses >10% with p<0.01, or full outage.
- Action: flip flag to 100% control via {args.platform or 'LaunchDarkly/Optimizely'}.
- Owner: {args.owner or 'TBD'} — paged via on-call rotation.

## Risks
{('- Runtime > 4 weeks: novelty/seasonality may bias results.' if days > 28 else '- None flagged automatically.')}
"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="")
    p.add_argument("--hypothesis", default="")
    p.add_argument("--metric-name", default="")
    p.add_argument("--metric-type", choices=["proportion", "mean"], required=True)
    p.add_argument("--baseline", type=float, required=True)
    p.add_argument("--stddev", type=float, default=0.0, help="Required for --metric-type=mean")
    p.add_argument("--mde", type=float, required=True, help="Relative MDE, e.g. 0.05 for 5%")
    p.add_argument("--daily-users", type=int, required=True)
    p.add_argument("--variants", type=int, default=2)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.8)
    p.add_argument("--platform", default="LaunchDarkly")
    p.add_argument("--owner", default="")
    p.add_argument("--guardrails", default="")
    args = p.parse_args()

    if args.metric_type == "proportion":
        n = sample_size_proportion(args.baseline, args.mde, args.alpha, args.power)
    else:
        if args.stddev <= 0:
            print("--stddev required (>0) for --metric-type=mean", file=sys.stderr)
            return 2
        n = sample_size_mean(args.baseline, args.stddev, args.mde, args.alpha, args.power)

    total = n * args.variants
    days = total / max(args.daily_users, 1)
    print(render_brief(args, n, total, days))
    return 0


if __name__ == "__main__":
    sys.exit(main())
