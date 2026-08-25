#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify that the legacy werewolf engine still matches its golden trace."""

import json
import sys
from pathlib import Path

from generate_werewolf_golden_trace import build_trace_suite


def main() -> int:
    """Compare the current legacy behavior with the checked-in fixture."""
    fixture_path = Path(__file__).resolve().parents[2] / "docs/fixtures/werewolf-golden-trace-suite.json"
    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    actual = build_trace_suite()

    if actual != expected:
        print(f"Golden trace mismatch: {fixture_path}", file=sys.stderr)
        return 1

    print(f"Golden trace verified: {fixture_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
