from __future__ import annotations

from datetime import date, timedelta

import httpx

from src.providers.base import GoldProvider, HistoricalEntry, PriceResult
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

        price = float(data.get("price") or data.get("price_gram_24k") or 0)
        if price <= 0:
            raise ValueError(f"GoldAPI returned invalid price: {data}")

        today = date.today().isoformat()
        logger.info("goldapi_current_price_fetched", price=price, date=today)
        return PriceResult(
            price_usd=price,
            date=today,
            source=self.name,
            open_usd=data.get("open_price"),
            high_usd=data.get("high_price"),
            low_usd=data.get("low_price"),
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

                price = float(data.get("price") or data.get("close_price") or 0)
                if price > 0:
                    entries.append(HistoricalEntry(
                        date=current.isoformat(),
                        price_usd=price,
                        open_usd=data.get("open_price"),
                        high_usd=data.get("high_price"),
                        low_usd=data.get("low_price"),
                        source=self.name,
                    ))
            except Exception as exc:
                logger.warning("goldapi_historical_day_failed", date=current.isoformat(), error=str(exc))

            current += timedelta(days=1)

        logger.info("goldapi_historical_fetched", count=len(entries), days=days)
        return sorted(entries, key=lambda e: e.date)
