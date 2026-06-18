#!/usr/bin/env python3
"""
Fetch the current gold price and persist it to the database.
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
    result = await svc.get_current_price()

    logger.info(
        "collect_success",
        price=result.price_usd,
        date=result.date,
        source=result.source,
    )
    print(f"Collected: ${result.price_usd:,.2f} on {result.date} from {result.source}")


def main() -> None:
    asyncio.run(collect())


if __name__ == "__main__":
    main()
