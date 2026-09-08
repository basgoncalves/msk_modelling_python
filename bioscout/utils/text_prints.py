"""Console/log formatting helpers -- the shape bioscout's output already has.

Today the codebase writes its progress with ad-hoc ``print()`` calls, and the
convention that emerged is a bracketed tag naming the stage: ``[scale] ...``,
``[Session] ...``, ``[simulate so] ...``. This module is the seed for making
that one thing instead of several hundred (docs/RESTRUCTURE_PLAN.md, stage 11).

SEED MODULE: nothing has been migrated onto it yet, deliberately. Rewriting
every print in the package in one pass would bury a real behaviour change in
thousands of cosmetic lines; the plan is to adopt these as each module is next
touched for its own reasons.

    from bioscout.utils.text_prints import tagged, warn, rule

    tagged("scale", f"wrote {path}")          # [scale] wrote ...
    warn("scale", "MeasurementSet is empty")  # [scale] [WARNING] ...
"""
from __future__ import annotations

import sys

__all__ = ["tagged", "warn", "fail", "rule", "kv"]


def tagged(tag, message, stream=None):
    """``[tag] message`` -- the house style for a progress line."""
    print(f"[{tag}] {message}", file=stream or sys.stdout, flush=True)


def warn(tag, message, stream=None):
    """``[tag] [WARNING] message`` -- something is off, the run continues."""
    print(f"[{tag}] [WARNING] {message}", file=stream or sys.stdout, flush=True)


def fail(tag, message, stream=None):
    """``[tag] [ERROR] message`` -- to stderr, because it ended something."""
    print(f"[{tag}] [ERROR] {message}", file=stream or sys.stderr, flush=True)


def rule(title="", width=72, char="="):
    """A section rule, optionally with a centred title."""
    if not title:
        return char * width
    pad = max(0, width - len(title) - 2)
    left = pad // 2
    return f"{char * left} {title} {char * (pad - left)}"


def kv(pairs, sep="  "):
    """``a=1  b=2`` from a dict or pairs -- the run-header style."""
    items = pairs.items() if hasattr(pairs, "items") else pairs
    return sep.join(f"{k}={v}" for k, v in items)
