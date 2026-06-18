#!/usr/bin/env python3
"""
Backfill historical gold price data into the local SQLite database.

Usage:
    python scripts/backfill_history.py --days 365
    python scripts/backfill_history.py --days 1825
    python scripts/backfill_history.py --days 3650
    python scripts/backfill_history.py --full
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


async def backfill(days: int) -> None:
    config = get_config()
    configure_logging(level=config.logging.level, fmt="json")
    logger = get_logger("backfill_history")

    init_db()
    logger.info("backfill_start", days=days)

    svc = GoldService()
    count = await svc.ensure_history_loaded(days)
    logger.info("backfill_prices_stored", count=count)

    ind_svc = IndicatorService()
    ind_count = ind_svc.compute_and_store()
    logger.info("backfill_indicators_computed", count=ind_count)

    print(f"Backfill complete: {count} price records, {ind_count} indicator records stored.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical gold price data.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--days", type=int, help="Number of days to backfill (e.g. 365, 1825, 3650)")
    group.add_argument("--full", action="store_true", help="Backfill full 10 years (3650 days)")
    args = parser.parse_args()

    days = 3650 if args.full else args.days
    if days <= 0:
        print("Error: --days must be a positive integer.", file=sys.stderr)
        sys.exit(1)

    asyncio.run(backfill(days))


if __name__ == "__main__":
    main()
