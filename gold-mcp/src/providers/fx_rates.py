from __future__ import annotations

import time

import httpx

from src.utils.logging import get_logger

logger = get_logger(__name__)

_EXCHANGERATE_URL = "https://open.er-api.com/v6/latest/USD"


class FXRateProvider:
    """Fetches USD → target currency exchange rates.

    Primary source: open.er-api.com (free, no key required).
    Fallback: yfinance ticker <CURRENCY>USD=X.
    Results are cached in-memory for cache_ttl_seconds.
    """

    def __init__(self, cache_ttl_seconds: int = 3600) -> None:
        self._ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[float, float]] = {}  # currency -> (rate, expires_at)

    async def get_rate(self, from_currency: str, to_currency: str) -> float:
        if from_currency == to_currency:
            return 1.0

        cache_key = f"{from_currency}/{to_currency}"
        cached_rate, expires_at = self._cache.get(cache_key, (None, 0))
        if cached_rate is not None and time.monotonic() < expires_at:
            logger.debug("fx_rate_cache_hit", pair=cache_key, rate=cached_rate)
            return cached_rate

        rate = await self._fetch_via_exchangerate_api(from_currency, to_currency)
        if rate is None:
            rate = await self._fetch_via_yfinance(from_currency, to_currency)
        if rate is None:
            raise RuntimeError(f"Could not obtain FX rate for {from_currency} → {to_currency}")

        self._cache[cache_key] = (rate, time.monotonic() + self._ttl)
        logger.info("fx_rate_fetched", pair=cache_key, rate=rate)
        return rate

    async def _fetch_via_exchangerate_api(self, from_currency: str, to_currency: str) -> float | None:
        try:
            url = f"https://open.er-api.com/v6/latest/{from_currency}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            rate = data.get("rates", {}).get(to_currency)
            if rate:
                return float(rate)
        except Exception as exc:
            logger.warning("fx_exchangerate_api_failed", error=str(exc))
        return None

    async def _fetch_via_yfinance(self, from_currency: str, to_currency: str) -> float | None:
        try:
            import yfinance as yf
            ticker = f"{to_currency}{from_currency}=X"
            data = yf.Ticker(ticker)
            info = data.fast_info
            price = getattr(info, "last_price", None)
            if price and price > 0:
                return float(price)
            # Try reverse ticker
            ticker_rev = f"{from_currency}{to_currency}=X"
            data_rev = yf.Ticker(ticker_rev)
            info_rev = data_rev.fast_info
            price_rev = getattr(info_rev, "last_price", None)
            if price_rev and price_rev > 0:
                return 1.0 / float(price_rev)
        except Exception as exc:
            logger.warning("fx_yfinance_failed", error=str(exc))
        return None


_fx_provider: FXRateProvider | None = None


def get_fx_provider() -> FXRateProvider:
    global _fx_provider
    if _fx_provider is None:
        from src.config import get_config
        config = get_config()
        _fx_provider = FXRateProvider(cache_ttl_seconds=config.fx.cache_ttl_seconds)
    return _fx_provider
