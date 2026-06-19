from __future__ import annotations

from datetime import date, timedelta

import httpx

from src.providers.base import GoldProvider, HistoricalEntry, PriceResult, derive_carat_prices
from src.utils.logging import get_logger

logger = get_logger(__name__)

METALSDEV_BASE = "https://api.metals.dev/v1"


class MetalsDevProvider(GoldProvider):
    """Metals.dev provider. Supports USD (default) and INR via the currency param."""

    def __init__(self, api_key: str = "", currency: str = "USD"):
        self.api_key = api_key
        self.currency = currency
        self.name = f"metalsdev" if currency == "USD" else f"metalsdev_{currency.lower()}"

    def supports_current_price(self) -> bool:
        return bool(self.api_key)

    def supports_historical(self) -> bool:
        return bool(self.api_key)

    async def get_current_price(self) -> PriceResult:
        if not self.api_key:
            raise ValueError("Metals.dev requires an API key")

        url = f"{METALSDEV_BASE}/latest"
        params = {"api_key": self.api_key, "currency": self.currency, "unit": "g"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        metals = data.get("metals", {})
        price = float(metals.get("gold") or metals.get("XAU") or 0)
        if price <= 0:
            raise ValueError(f"Metals.dev returned invalid price: {data}")

        today = date.today().isoformat()
        price_type = "local" if self.currency == "USD" else "local"
        logger.info("metalsdev_current_price_fetched", price=price, currency=self.currency, date=today)
        return PriceResult(
            price=price,
            currency=self.currency,
            carat="24K",
            source=self.name,
            price_type=price_type,
            date=today,
            carat_prices=derive_carat_prices(price),
        )

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
                "currency": self.currency,
                "unit": "g",
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
                        price=price,
                        currency=self.currency,
                        carat="24K",
                        price_type="local",
                        calculated=False,
                        source=self.name,
                    ))
            except Exception as exc:
                logger.warning("metalsdev_historical_day_failed", date=current.isoformat(), error=str(exc))

            current += timedelta(days=1)

        logger.info("metalsdev_historical_fetched", count=len(entries), currency=self.currency, days=days)
        return sorted(entries, key=lambda e: e.date)
