from __future__ import annotations

import argparse
import sys

from dev_seed.config import (
    DEFAULT_DAYS,
    DEFAULT_SEED,
    DEFAULT_USER_COUNT,
)
from dev_seed.loader import format_report, run_seed
from dev_seed.personas import PERSONAS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m dev_seed",
        description="Populate the local DB with deterministic mock mood-tracker data.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"RNG seed for reproducible data (default: {DEFAULT_SEED})",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=DEFAULT_USER_COUNT,
        help=(
            f"Number of seed personas to create (1–{len(PERSONAS)}, default: {DEFAULT_USER_COUNT})"
        ),
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"History window in days (default: {DEFAULT_DAYS}; not every day is filled)",
    )
    parser.add_argument(
        "--entries-per-day-min",
        type=int,
        default=None,
        help="Override persona entries/day min when a day is logged (default: per persona)",
    )
    parser.add_argument(
        "--entries-per-day-max",
        type=int,
        default=None,
        help="Override persona entries/day max when a day is logged (default: per persona)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = run_seed(
            seed=args.seed,
            user_count=args.users,
            days=args.days,
            entries_per_day_min=args.entries_per_day_min,
            entries_per_day_max=args.entries_per_day_max,
        )
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    print(format_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
