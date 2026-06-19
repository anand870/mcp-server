#!/usr/bin/env python3
"""
Backfill historical gold price data for all enabled currencies into the local SQLite database.

Usage:
    python scripts/backfill_history.py --days 365
    python scripts/backfill_history.py --days 1825
    python scripts/backfill_history.py --days 3650
    python scripts/backfill_history.py --full
    python scripts/backfill_history.py --days 365 --currency USD
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.database import init_db
from src.services.gold_service import GoldService
from src.services.indicator_service import IndicatorService
from src.utils.logging import configure_logging, get_logger


async def backfill(days: int, currency: str | None = None) -> None:
    config = get_config()
    configure_logging(level=config.logging.level, fmt="json")
    logger = get_logger("backfill_history")

    init_db()
    logger.info("backfill_start", days=days, currency=currency or "all")

    svc = GoldService()
    currencies = [currency] if currency else config.enabled_currencies()
    total = 0

    for cur in currencies:
        try:
            count = await svc.ensure_history_loaded(days, currency=cur, carat="24K")
            logger.info("backfill_currency_done", currency=cur, count=count)
            total += count
            print(f"[{cur}] {count} price records stored.")
        except Exception as exc:
            logger.warning("backfill_currency_failed", currency=cur, error=str(exc))
            print(f"[{cur}] FAILED: {exc}", file=sys.stderr)

    ind_svc = IndicatorService()
    ind_count = ind_svc.compute_and_store()
    logger.info("backfill_indicators_computed", count=ind_count)

    print(f"\nBackfill complete: {total} price records, {ind_count} indicator records stored.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical gold price data.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--days", type=int, help="Number of days to backfill (e.g. 365, 1825, 3650)")
    group.add_argument("--full", action="store_true", help="Backfill full 10 years (3650 days)")
    parser.add_argument(
        "--currency",
        type=str,
        default=None,
        help="Backfill a specific currency only (e.g. USD). Defaults to all enabled currencies.",
    )
    args = parser.parse_args()

    days = 3650 if args.full else args.days
    if days <= 0:
        print("Error: --days must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(backfill(days, currency=args.currency))


if __name__ == "__main__":
    main()
