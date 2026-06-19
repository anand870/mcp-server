from __future__ import annotations

import re
from datetime import date

import httpx

from src.providers.base import GoldProvider, HistoricalEntry, PriceResult, derive_carat_prices
from src.utils.logging import get_logger

logger = get_logger(__name__)

_KT_URL = "https://api.khaleejtimes.com/JoyalukkasGold_ajx/get_Gold_data_new_countries"
_KT_HEADERS = {"origin": "https://www.khaleejtimes.com"}

_CARAT_TYPES = {"24K", "22K", "21K", "18K"}


def _parse_price(value: str) -> float | None:
    """Strip commas/whitespace and return float, or None if zero/empty."""
    numeric = re.sub(r"[^\d.]", "", value or "")
    if not numeric:
        return None
    f = float(numeric)
    return f if f > 0 else None


def _latest_price(row: dict) -> float | None:
    """Return the most recent non-zero price: evening → afternoon → morning."""
    for slot in ("evening", "afternoon", "morning"):
        p = _parse_price(row.get(slot, ""))
        if p is not None:
            return p
    return None


class KhaleejTimesProvider(GoldProvider):
    """Khaleej Times gold rate API — live INR per-gram prices (24K/22K/21K/18K).

    Provides morning, afternoon, and evening updates; the latest non-zero slot
    is used so the price is always as fresh as possible within the trading day.
    """

    name = "khaleejtimes"

    def supports_current_price(self) -> bool:
        return True

    def supports_historical(self) -> bool:
        return False

    async def get_current_price(self) -> PriceResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                _KT_URL,
                params={"country": "india"},
                headers=_KT_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()

        rates: list[dict] = data.get("rates", [])

        provider_carats: dict[str, float] = {}
        for row in rates:
            carat_type = (row.get("type") or "").strip()
            if carat_type not in _CARAT_TYPES:
                continue
            price = _latest_price(row)
            if price is not None:
                provider_carats[carat_type] = price

        price_24k = provider_carats.get("24K")
        if price_24k is None or price_24k <= 0:
            raise ValueError(f"KhaleejTimes: missing or invalid 24K price: {provider_carats}")

        carat_prices = derive_carat_prices(price_24k, provider_carats=provider_carats)
        today = date.today().isoformat()

        logger.info(
            "khaleejtimes_price_fetched",
            price_24k=price_24k,
            currency="INR",
            date=today,
            kt_date=data.get("date"),
            carats_supplied=list(provider_carats.keys()),
        )
        return PriceResult(
            price=price_24k,
            currency="INR",
            carat="24K",
            source=self.name,
            price_type="local",
            date=today,
            carat_prices=carat_prices,
        )

    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        raise NotImplementedError("KhaleejTimes does not provide historical data")
