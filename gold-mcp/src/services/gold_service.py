from __future__ import annotations

from datetime import date, timedelta

from src.database import (
    GoldIndicatorRepository,
    GoldPriceRepository,
    session_scope,
)
from src.providers.manager import get_provider_manager
from src.schemas import GoldHistoryEntry, GoldHistoryResponse, GoldPriceResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)


class GoldService:
    async def get_current_price(self) -> GoldPriceResponse:
        manager = get_provider_manager()
        result = await manager.get_current_price()

        with session_scope() as session:
            repo = GoldPriceRepository(session)
            repo.upsert(
                date_str=result.date,
                price_usd=result.price_usd,
                source=result.source,
                open_usd=result.open_usd,
                high_usd=result.high_usd,
                low_usd=result.low_usd,
            )

        from datetime import datetime
        return GoldPriceResponse(
            price_usd=result.price_usd,
            date=result.date,
            source=result.source,
            timestamp=datetime.utcnow().isoformat() + "Z",
            open_usd=result.open_usd,
            high_usd=result.high_usd,
            low_usd=result.low_usd,
        )

    async def get_history(self, days: int) -> GoldHistoryResponse:
        end = date.today()
        start = end - timedelta(days=days)
        start_str = start.isoformat()
        end_str = end.isoformat()

        with session_scope() as session:
            repo = GoldPriceRepository(session)
            db_records = repo.get_range(start_str, end_str)
            db_count = len(db_records)

        if db_count < max(5, days // 3):
            logger.info("gold_service_history_fetching_from_provider", days=days, db_count=db_count)
            manager = get_provider_manager()
            entries = await manager.get_historical(days)
            with session_scope() as session:
                repo = GoldPriceRepository(session)
                for e in entries:
                    repo.upsert(
                        date_str=e.date,
                        price_usd=e.price_usd,
                        source=e.source,
                        open_usd=e.open_usd,
                        high_usd=e.high_usd,
                        low_usd=e.low_usd,
                    )
            with session_scope() as session:
                repo = GoldPriceRepository(session)
                db_records = repo.get_range(start_str, end_str)
                history_entries = [
                    GoldHistoryEntry(
                        date=r.date,
                        price_usd=r.price_usd,
                        open_usd=r.open_usd,
                        high_usd=r.high_usd,
                        low_usd=r.low_usd,
                        source=r.source,
                    )
                    for r in db_records
                ]
        else:
            history_entries = [
                GoldHistoryEntry(
                    date=r.date,
                    price_usd=r.price_usd,
                    open_usd=r.open_usd,
                    high_usd=r.high_usd,
                    low_usd=r.low_usd,
                    source=r.source,
                )
                for r in db_records
            ]

        return GoldHistoryResponse(
            entries=history_entries,
            period_days=days,
            start_date=start_str,
            end_date=end_str,
            count=len(history_entries),
        )

    async def ensure_history_loaded(self, days: int) -> int:
        manager = get_provider_manager()
        entries = await manager.get_historical(days)
        count = 0
        with session_scope() as session:
            repo = GoldPriceRepository(session)
            for e in entries:
                repo.upsert(
                    date_str=e.date,
                    price_usd=e.price_usd,
                    source=e.source,
                    open_usd=e.open_usd,
                    high_usd=e.high_usd,
                    low_usd=e.low_usd,
                )
                count += 1
        logger.info("gold_service_history_loaded", days=days, count=count)
        return count
