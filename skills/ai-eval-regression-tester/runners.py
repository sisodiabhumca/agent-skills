"""Sample candidate runners.

`echo` is deterministic and used for the demo suite. For real evals, write a
runner that calls your LLM endpoint or local model.
"""
from __future__ import annotations


def echo(case_input: str) -> str:
    """Trivial runner that demonstrates a passing case for the demo suite."""
    if "refund" in case_input.lower():
        return (
            "Per our return policy, you may contact the support team within 60 days. "
            "If you're outside that window, reach out and we'll review case-by-case."
        )
    if "json" in case_input.lower():
        return '{"answer": "ok", "citation": "kb#42"}'
    return "I don't know the answer to that."
