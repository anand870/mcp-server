from __future__ import annotations

from datetime import date, datetime, timedelta

from src.config import get_config
from src.database import GoldPriceRepository, session_scope
from src.providers.manager import get_provider_manager
from src.schemas import CaratPriceDetail, GoldHistoryEntry, GoldHistoryResponse, GoldPriceResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _resolve_currency_carat(currency: str | None, carat: str | None) -> tuple[str, str]:
    config = get_config()
    return (
        currency or config.default_currency,
        carat or config.default_carat,
    )


class GoldService:
    async def get_current_price(
        self, currency: str | None = None, carat: str | None = None
    ) -> GoldPriceResponse:
        currency, carat = _resolve_currency_carat(currency, carat)
        manager = get_provider_manager()
        result = await manager.get_current_price(currency=currency)

        with session_scope() as session:
            repo = GoldPriceRepository(session)
            for cp in result.carat_prices:
                repo.upsert(
                    date_str=result.date,
                    price=cp.price,
                    currency=result.currency,
                    carat=cp.carat,
                    source=result.source,
                    price_type=result.price_type,
                    calculated=cp.calculated,
                    open=result.open if cp.carat == "24K" else None,
                    high=result.high if cp.carat == "24K" else None,
                    low=result.low if cp.carat == "24K" else None,
                )

        requested_price = next(
            (cp.price for cp in result.carat_prices if cp.carat == carat),
            result.price,
        )

        return GoldPriceResponse(
            price=requested_price,
            currency=result.currency,
            carat=carat,
            price_type=result.price_type,
            date=result.date,
            source=result.source,
            timestamp=datetime.utcnow().isoformat() + "Z",
            all_carats=[
                CaratPriceDetail(carat=cp.carat, price=cp.price, calculated=cp.calculated)
                for cp in result.carat_prices
            ],
            open=result.open if carat == "24K" else None,
            high=result.high if carat == "24K" else None,
            low=result.low if carat == "24K" else None,
        )

    async def get_history(
        self, days: int, currency: str | None = None, carat: str | None = None
    ) -> GoldHistoryResponse:
        currency, carat = _resolve_currency_carat(currency, carat)
        end = date.today()
        start = end - timedelta(days=days)
        start_str = start.isoformat()
        end_str = end.isoformat()

        with session_scope() as session:
            repo = GoldPriceRepository(session)
            db_records = repo.get_range(start_str, end_str, currency=currency, carat=carat)
            db_count = len(db_records)

        if db_count < max(5, days // 3):
            logger.info(
                "gold_service_history_fetching_from_provider",
                days=days, db_count=db_count, currency=currency, carat=carat,
            )
            manager = get_provider_manager()
            entries = await manager.get_historical(days, currency=currency)
            with session_scope() as session:
                repo = GoldPriceRepository(session)
                for e in entries:
                    repo.upsert(
                        date_str=e.date,
                        price=e.price,
                        currency=e.currency,
                        carat=e.carat,
                        source=e.source,
                        price_type=e.price_type,
                        calculated=e.calculated,
                        open=e.open,
                        high=e.high,
                        low=e.low,
                    )
            with session_scope() as session:
                repo = GoldPriceRepository(session)
                db_records = repo.get_range(start_str, end_str, currency=currency, carat=carat)

        history_entries = [
            GoldHistoryEntry(
                date=r.date,
                price=r.price,
                currency=r.currency,
                carat=r.carat,
                price_type=r.price_type,
                source=r.source,
                open=r.open,
                high=r.high,
                low=r.low,
            )
            for r in db_records
        ]

        return GoldHistoryResponse(
            entries=history_entries,
            period_days=days,
            start_date=start_str,
            end_date=end_str,
            count=len(history_entries),
            currency=currency,
            carat=carat,
        )

    async def get_all_current_prices(self) -> dict[str, dict[str, CaratPriceDetail]]:
        """Fetch current prices for all enabled currencies and carats."""
        config = get_config()
        manager = get_provider_manager()
        result: dict[str, dict[str, CaratPriceDetail]] = {}

        for currency in config.enabled_currencies():
            try:
                pr = await manager.get_current_price(currency=currency)
                with session_scope() as session:
                    repo = GoldPriceRepository(session)
                    for cp in pr.carat_prices:
                        repo.upsert(
                            date_str=pr.date,
                            price=cp.price,
                            currency=pr.currency,
                            carat=cp.carat,
                            source=pr.source,
                            price_type=pr.price_type,
                            calculated=cp.calculated,
                            open=pr.open if cp.carat == "24K" else None,
                            high=pr.high if cp.carat == "24K" else None,
                            low=pr.low if cp.carat == "24K" else None,
                        )
                result[currency] = {
                    cp.carat: CaratPriceDetail(
                        carat=cp.carat,
                        price=cp.price,
                        calculated=cp.calculated,
                    )
                    for cp in pr.carat_prices
                }
            except Exception as exc:
                logger.warning("get_all_prices_currency_failed", currency=currency, error=str(exc))
                result[currency] = {}

        return result

    async def ensure_history_loaded(
        self, days: int, currency: str = "USD", carat: str = "24K"
    ) -> int:
        manager = get_provider_manager()
        entries = await manager.get_historical(days, currency=currency)
        count = 0
        with session_scope() as session:
            repo = GoldPriceRepository(session)
            for e in entries:
                if e.carat == carat:
                    repo.upsert(
                        date_str=e.date,
                        price=e.price,
                        currency=e.currency,
                        carat=e.carat,
                        source=e.source,
                        price_type=e.price_type,
                        calculated=e.calculated,
                        open=e.open,
                        high=e.high,
                        low=e.low,
                    )
                    count += 1
        logger.info("gold_service_history_loaded", days=days, currency=currency, carat=carat, count=count)
        return count
