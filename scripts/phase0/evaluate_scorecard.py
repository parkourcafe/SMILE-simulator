#!/usr/bin/env python3
"""Validate a completed Phase 0 scorecard and render the fixed decision report."""

from __future__ import annotations

import argparse
from pathlib import Path

from evidence import EvidenceError, evaluate_scorecard, render_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the ZubiLook Phase 0 scorecard")
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--scorecard", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--recurring-identity-failure",
        action="store_true",
        help="force NO-GO when reviewers confirm a recurring identity-preservation failure",
    )
    args = parser.parse_args()

    try:
        evaluation = evaluate_scorecard(
            args.results,
            args.scorecard,
            recurring_identity_failure=args.recurring_identity_failure,
        )
    except EvidenceError as exc:
        raise SystemExit(f"Invalid Phase 0 evidence: {exc}") from exc

    args.output.write_text(render_report(evaluation), encoding="utf-8")
    print(f"Decision: {evaluation.decision}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
