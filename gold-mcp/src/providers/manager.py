from __future__ import annotations

import asyncio

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_config, get_settings
from src.providers.base import GoldProvider, HistoricalEntry, PriceResult
from src.providers.freegoldapi import FreeGoldAPIProvider
from src.providers.goldapi import GoldAPIProvider
from src.providers.metalsdev import MetalsDevProvider
from src.providers.yahoofinance import YahooFinanceProvider
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _build_providers(settings) -> dict[str, GoldProvider]:
    return {
        "freegoldapi": FreeGoldAPIProvider(api_key=settings.freegoldapi_key),
        "metalsdev": MetalsDevProvider(api_key=settings.metalsdev_key),
        "yahoofinance": YahooFinanceProvider(),
        "goldapi": GoldAPIProvider(api_key=settings.goldapi_key),
    }


class ProviderManager:
    def __init__(self):
        config = get_config()
        settings = get_settings()
        self._providers = _build_providers(settings)
        self._current_order = config.providers.current_price_order
        self._historical_order = config.providers.historical_order
        self._retry_cfg = config.providers.retry

    def _make_retry(self):
        return retry(
            stop=stop_after_attempt(self._retry_cfg.attempts),
            wait=wait_exponential(
                multiplier=self._retry_cfg.wait_multiplier,
                min=self._retry_cfg.wait_min,
                max=self._retry_cfg.wait_max,
            ),
            retry=retry_if_exception_type(Exception),
            reraise=True,
        )

    async def get_current_price(self) -> PriceResult:
        last_exc: Exception | None = None
        for name in self._current_order:
            provider = self._providers.get(name)
            if provider is None or not provider.supports_current_price():
                logger.debug("provider_skipped", provider=name, reason="unsupported_or_missing")
                continue
            try:
                logger.info("provider_attempt_current", provider=name)
                result = await self._fetch_with_retry(provider.get_current_price)
                logger.info("provider_success_current", provider=name, price=result.price_usd)
                return result
            except Exception as exc:
                logger.warning("provider_failed_current", provider=name, error=str(exc))
                last_exc = exc

        raise RuntimeError(f"All providers failed for current price. Last error: {last_exc}")

    async def get_historical(self, days: int) -> list[HistoricalEntry]:
        last_exc: Exception | None = None
        for name in self._historical_order:
            provider = self._providers.get(name)
            if provider is None or not provider.supports_historical():
                logger.debug("provider_skipped", provider=name, reason="unsupported_or_missing")
                continue
            try:
                logger.info("provider_attempt_historical", provider=name, days=days)
                result = await self._fetch_with_retry(provider.get_historical, days)
                if result:
                    logger.info("provider_success_historical", provider=name, count=len(result))
                    return result
                raise ValueError(f"Provider {name} returned empty historical data")
            except Exception as exc:
                logger.warning("provider_failed_historical", provider=name, error=str(exc))
                last_exc = exc

        raise RuntimeError(f"All providers failed for historical data. Last error: {last_exc}")

    async def _fetch_with_retry(self, fn, *args):
        cfg = self._retry_cfg
        last_exc: Exception | None = None
        for attempt in range(cfg.attempts):
            try:
                return await fn(*args)
            except Exception as exc:
                last_exc = exc
                if attempt < cfg.attempts - 1:
                    wait = min(cfg.wait_min * (cfg.wait_multiplier ** attempt), cfg.wait_max)
                    logger.warning("provider_retry", attempt=attempt + 1, wait=wait, error=str(exc))
                    await asyncio.sleep(wait)
        raise last_exc


_manager: ProviderManager | None = None


def get_provider_manager() -> ProviderManager:
    global _manager
    if _manager is None:
        _manager = ProviderManager()
    return _manager
