from __future__ import annotations

from datetime import date, timedelta

import httpx

from src.providers.base import TROY_OZ_PER_GRAM, GoldProvider, HistoricalEntry, PriceResult, derive_carat_prices
from src.utils.logging import get_logger

logger = get_logger(__name__)

GOLDAPI_BASE = "https://www.goldapi.io/api"


class GoldAPIProvider(GoldProvider):
    name = "goldapi"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def supports_current_price(self) -> bool:
        return bool(self.api_key)

    def supports_historical(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {
            "x-access-token": self.api_key,
            "Content-Type": "application/json",
        }

    async def get_current_price(self) -> PriceResult:
        if not self.api_key:
            raise ValueError("GoldAPI requires an API key")

        url = f"{GOLDAPI_BASE}/XAU/USD"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            data = response.json()

        # price_gram_24k is already per gram; price is per troy oz
        price_gram = data.get("price_gram_24k")
        if price_gram:
            price = round(float(price_gram), 4)
        else:
            price_toz = float(data.get("price") or 0)
            if price_toz <= 0:
                raise ValueError(f"GoldAPI returned invalid price: {data}")
            price = round(price_toz / TROY_OZ_PER_GRAM, 4)

        def _to_gram(v):
            return round(float(v) / TROY_OZ_PER_GRAM, 4) if v else None

        today = date.today().isoformat()
        logger.info("goldapi_current_price_fetched", price=price, date=today)
        return PriceResult(
            price=price,
            currency="USD",
            carat="24K",
            source=self.name,
            price_type="local",
            date=today,
            carat_prices=derive_carat_prices(price),
            open=_to_gram(data.get("open_price")),
            high=_to_gram(data.get("high_price")),
            low=_to_gram(data.get("low_price")),
        )

    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        if not self.api_key:
            raise ValueError("GoldAPI requires an API key")

        entries: list[HistoricalEntry] = []
        end = date.today()
        start = end - timedelta(days=days)

        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            url = f"{GOLDAPI_BASE}/XAU/USD/{date_str}"
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, headers=self._headers())
                    response.raise_for_status()
                    data = response.json()

                price_toz = float(data.get("price") or data.get("close_price") or 0)
                if price_toz > 0:
                    def _g(v):
                        return round(float(v) / TROY_OZ_PER_GRAM, 4) if v else None
                    entries.append(HistoricalEntry(
                        date=current.isoformat(),
                        price=round(price_toz / TROY_OZ_PER_GRAM, 4),
                        currency="USD",
                        carat="24K",
                        price_type="local",
                        calculated=False,
                        source=self.name,
                        open=_g(data.get("open_price")),
                        high=_g(data.get("high_price")),
                        low=_g(data.get("low_price")),
                    ))
            except Exception as exc:
                logger.warning("goldapi_historical_day_failed", date=current.isoformat(), error=str(exc))

            current += timedelta(days=1)

        logger.info("goldapi_historical_fetched", count=len(entries), days=days)
        return sorted(entries, key=lambda e: e.date)
