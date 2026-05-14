#!/usr/bin/env python3
"""Vendor-neutral retry/backoff simulator for batch jobs.

Stdlib-only Monte Carlo simulation.
"""

import argparse
import json
import random
import statistics
import sys


def delay_for_attempt(strategy, base_delay, attempt_index, rng):
    # attempt_index is 1-based for the *next* attempt after a failure
    if strategy == "fixed":
        return base_delay
    if strategy == "exponential":
        return base_delay * (2 ** (attempt_index - 1))
    if strategy == "exponential_jitter":
        exp = base_delay * (2 ** (attempt_index - 1))
        return rng.uniform(0.5 * exp, 1.5 * exp)
    raise ValueError(f"unknown strategy: {strategy}")


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def simulate_one(cfg, rng):
    attempts_max = int(cfg["attempts_max"])
    work = float(cfg["work_seconds_per_attempt"])
    p_fail = float(cfg["failure_probability"])
    base_delay = float(cfg["base_delay_seconds"])
    strategy = cfg["strategy"]

    total = 0.0
    backoff_total = 0.0
    attempts = 0
    success = False

    for attempt in range(1, attempts_max + 1):
        attempts += 1
        total += work
        if rng.random() >= p_fail:
            success = True
            break
        if attempt < attempts_max:
            d = delay_for_attempt(strategy, base_delay, attempt, rng)
            total += d
            backoff_total += d

    return {
        "success": success,
        "attempts": attempts,
        "total_seconds": total,
        "backoff_seconds": backoff_total,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    cfg = json.load(open(args.config, "r", encoding="utf-8"))

    required = [
        "attempts_max",
        "base_delay_seconds",
        "strategy",
        "failure_probability",
        "work_seconds_per_attempt",
        "trials",
    ]
    for k in required:
        if k not in cfg:
            raise SystemExit(f"Missing config key: {k}")

    if cfg["strategy"] not in {"fixed", "exponential", "exponential_jitter"}:
        raise SystemExit("strategy must be fixed|exponential|exponential_jitter")

    p_fail = float(cfg["failure_probability"])
    if not (0.0 <= p_fail <= 1.0):
        raise SystemExit("failure_probability must be between 0 and 1")

    trials = int(cfg["trials"])
    if trials <= 0:
        raise SystemExit("trials must be > 0")

    rng = random.Random(args.seed)

    results = [simulate_one(cfg, rng) for _ in range(trials)]

    success_rate = sum(1 for r in results if r["success"]) / trials
    attempts = [r["attempts"] for r in results]
    totals = [r["total_seconds"] for r in results]
    backoffs = [r["backoff_seconds"] for r in results]

    out = {
        "config": {
            "attempts_max": int(cfg["attempts_max"]),
            "base_delay_seconds": float(cfg["base_delay_seconds"]),
            "strategy": cfg["strategy"],
            "failure_probability": p_fail,
            "work_seconds_per_attempt": float(cfg["work_seconds_per_attempt"]),
            "trials": trials,
            "seed": args.seed,
        },
        "success_rate": round(success_rate, 4),
        "expected_attempts": round(statistics.mean(attempts), 4),
        "expected_backoff_seconds": round(statistics.mean(backoffs), 4),
        "duration_seconds": {
            "mean": round(statistics.mean(totals), 4),
            "p50": round(percentile(totals, 0.50), 4),
            "p90": round(percentile(totals, 0.90), 4),
            "max": round(max(totals), 4),
        },
    }

    json.dump(out, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
