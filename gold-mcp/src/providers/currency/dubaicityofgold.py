from __future__ import annotations

from datetime import date

import httpx

from src.providers.base import GoldProvider, HistoricalEntry, PriceResult, derive_carat_prices
from src.utils.logging import get_logger

logger = get_logger(__name__)

_DCOG_URL = "https://dubaicityofgold.com/gold-rate-app/dcoggoldrate"
_DCOG_VENDOR_KEY = "DCOG_KEY_964592976"


class DubaiCityOfGoldProvider(GoldProvider):
    """Fetches AED gold rates from the Dubai City of Gold API.

    POST endpoint returns 24K / 22K / 21K / 18K / 14K prices.
    All returned carat prices are provider-supplied (calculated=False).
    """

    name = "dubaicityofgold"

    def supports_current_price(self) -> bool:
        return True

    def supports_historical(self) -> bool:
        return False

    async def get_current_price(self) -> PriceResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                _DCOG_URL,
                data={"vendor_key": _DCOG_VENDOR_KEY},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()

        if str(data.get("status")) != "1":
            raise ValueError(f"Dubai City of Gold API error: {data.get('msg', 'unknown')}")

        def _parse(key: str) -> float | None:
            val = data.get(key)
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        price_24k = _parse("gold_rate_24k")
        if not price_24k or price_24k <= 0:
            raise ValueError(f"Dubai City of Gold: invalid 24K price in response: {data}")

        provider_carats: dict[str, float] = {}
        for carat, key in [("24K", "gold_rate_24k"), ("22K", "gold_rate_22k"),
                            ("21K", "gold_rate_21k"), ("18K", "gold_rate_18k")]:
            v = _parse(key)
            if v and v > 0:
                provider_carats[carat] = v

        carat_prices = derive_carat_prices(price_24k, provider_carats=provider_carats)
        price_date = data.get("gold_rate_date", date.today().isoformat())

        logger.info("dcog_price_fetched", price_24k=price_24k, currency="AED", date=price_date)
        return PriceResult(
            price=price_24k,
            currency="AED",
            carat="24K",
            source=self.name,
            price_type="local",
            date=price_date,
            carat_prices=carat_prices,
        )

    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        raise NotImplementedError("Dubai City of Gold does not provide historical data")
