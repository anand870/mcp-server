from __future__ import annotations

from datetime import date, timedelta

import httpx

from src.providers.base import GoldProvider, HistoricalEntry, PriceResult
from src.utils.logging import get_logger

logger = get_logger(__name__)

METALSDEV_BASE = "https://api.metals.dev/v1"


class MetalsDevProvider(GoldProvider):
    name = "metalsdev"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key

    def supports_current_price(self) -> bool:
        return bool(self.api_key)

    def supports_historical(self) -> bool:
        return bool(self.api_key)

    async def get_current_price(self) -> PriceResult:
        if not self.api_key:
            raise ValueError("Metals.dev requires an API key")

        url = f"{METALSDEV_BASE}/latest"
        params = {"api_key": self.api_key, "currency": "USD", "unit": "toz"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        metals = data.get("metals", {})
        price = float(metals.get("gold") or metals.get("XAU") or 0)
        if price <= 0:
            raise ValueError(f"Metals.dev returned invalid price: {data}")

        today = date.today().isoformat()
        logger.info("metalsdev_current_price_fetched", price=price, date=today)
        return PriceResult(price_usd=price, date=today, source=self.name)

    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        if not self.api_key:
            raise ValueError("Metals.dev requires an API key")

        entries: list[HistoricalEntry] = []
        end = date.today()
        start = end - timedelta(days=days)

        current = start
        while current <= end:
            url = f"{METALSDEV_BASE}/historical"
            params = {
                "api_key": self.api_key,
                "currency": "USD",
                "unit": "toz",
                "date": current.isoformat(),
            }
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()

                metals = data.get("metals", {})
                price = float(metals.get("gold") or metals.get("XAU") or 0)
                if price > 0:
                    entries.append(HistoricalEntry(
                        date=current.isoformat(),
                        price_usd=price,
                        source=self.name,
                    ))
            except Exception as exc:
                logger.warning("metalsdev_historical_day_failed", date=current.isoformat(), error=str(exc))

            current += timedelta(days=1)

        logger.info("metalsdev_historical_fetched", count=len(entries), days=days)
        return sorted(entries, key=lambda e: e.date)
