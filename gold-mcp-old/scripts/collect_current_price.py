#!/usr/bin/env python3
"""
Fetch the current gold price for all enabled currencies and persist to the database.
Designed to run frequently (e.g. every 5 minutes via cron).

Usage:
    python scripts/collect_current_price.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import get_config
from src.database import init_db
from src.services.gold_service import GoldService
from src.utils.logging import configure_logging, get_logger


async def collect() -> None:
    config = get_config()
    configure_logging(level=config.logging.level, fmt="json")
    logger = get_logger("collect_current_price")

    init_db()
    logger.info("collect_start")

    svc = GoldService()
    currencies = config.enabled_currencies()

    for currency in currencies:
        try:
            result = await svc.get_current_price(currency=currency, carat="24K")
            logger.info(
                "collect_success",
                currency=result.currency,
                price=result.price,
                date=result.date,
                source=result.source,
                price_type=result.price_type,
            )
            carats_info = ", ".join(
                f"{cp['carat']}={cp['price']:.2f}{'*' if cp['calculated'] else ''}"
                for cp in result.all_carats
            )
            print(f"[{currency}] {result.source} ({result.price_type}): {carats_info} on {result.date}")
        except Exception as exc:
            logger.warning("collect_failed", currency=currency, error=str(exc))
            print(f"[{currency}] FAILED: {exc}", file=sys.stderr)


def main() -> None:
    asyncio.run(collect())


if __name__ == "__main__":
    main()
