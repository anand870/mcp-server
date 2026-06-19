#!/usr/bin/env python3
"""
Incrementally refresh gold price history for all enabled currencies (last N days)
and recompute USD 24K technical indicators.

Designed to run daily via cron or scheduler.

Usage:
    python scripts/refresh_history.py
    python scripts/refresh_history.py --days 30
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


async def refresh(days: int) -> None:
    config = get_config()
    configure_logging(level=config.logging.level, fmt="json")
    logger = get_logger("refresh_history")

    init_db()
    logger.info("refresh_start", days=days)

    svc = GoldService()
    currencies = config.enabled_currencies()
    total = 0

    for currency in currencies:
        try:
            count = await svc.ensure_history_loaded(days, currency=currency, carat="24K")
            logger.info("refresh_currency_done", currency=currency, count=count)
            total += count
            print(f"[{currency}] {count} price records updated.")
        except Exception as exc:
            logger.warning("refresh_currency_failed", currency=currency, error=str(exc))
            print(f"[{currency}] FAILED: {exc}", file=sys.stderr)

    ind_svc = IndicatorService()
    ind_count = ind_svc.compute_and_store()
    logger.info("refresh_indicators_recomputed", count=ind_count)

    print(f"\nRefresh complete: {total} price records, {ind_count} indicator records recomputed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh recent gold price history and recompute indicators.")
    parser.add_argument("--days", type=int, default=90, help="Days to refresh (default: 90)")
    args = parser.parse_args()
    asyncio.run(refresh(args.days))


if __name__ == "__main__":
    main()
