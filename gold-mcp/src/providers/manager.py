from __future__ import annotations

import asyncio

from src.config import get_config, get_settings
from src.providers.base import (
    GoldProvider,
    HistoricalEntry,
    PriceResult,
    derive_carat_prices,
)
from src.providers.currency.dubaicityofgold import DubaiCityOfGoldProvider
from src.providers.currency.igold import IgoldProvider
from src.providers.currency.khaleejtimes import KhaleejTimesProvider
from src.providers.freegoldapi import FreeGoldAPIProvider
from src.providers.fx_rates import FXRateProvider, get_fx_provider
from src.providers.goldapi import GoldAPIProvider
from src.providers.metalsdev import MetalsDevProvider
from src.providers.yahoofinance import YahooFinanceProvider
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _build_providers(settings) -> dict[str, GoldProvider]:
    return {
        "freegoldapi": FreeGoldAPIProvider(api_key=settings.freegoldapi_key),
        "metalsdev": MetalsDevProvider(api_key=settings.metalsdev_key, currency="USD"),
        "metalsdev_inr": MetalsDevProvider(api_key=settings.metalsdev_key, currency="INR"),
        "yahoofinance": YahooFinanceProvider(),
        "goldapi": GoldAPIProvider(api_key=settings.goldapi_key),
        "igold": IgoldProvider(),
        "dubaicityofgold": DubaiCityOfGoldProvider(),
        "khaleejtimes": KhaleejTimesProvider(),
    }


class ProviderManager:
    def __init__(self):
        config = get_config()
        settings = get_settings()
        self._providers = _build_providers(settings)
        self._currency_order = config.providers.currency_order
        self._historical_order = config.providers.historical_order
        self._retry_cfg = config.providers.retry
        self._fx: FXRateProvider = get_fx_provider()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def get_current_price(self, currency: str = "USD") -> PriceResult:
        order = self._currency_order.get(currency, [])
        last_exc: Exception | None = None

        for name in order:
            if name == "usd_conversion":
                try:
                    return await self._convert_from_usd(currency)
                except Exception as exc:
                    logger.warning("usd_conversion_failed", currency=currency, error=str(exc))
                    last_exc = exc
                continue

            provider = self._providers.get(name)
            if provider is None or not provider.supports_current_price():
                logger.debug("provider_skipped", provider=name, reason="unsupported_or_missing")
                continue
            try:
                logger.info("provider_attempt_current", provider=name, currency=currency)
                result = await self._fetch_with_retry(provider.get_current_price)
                logger.info("provider_success_current", provider=name, price=result.price, currency=currency)
                return result
            except Exception as exc:
                logger.warning("provider_failed_current", provider=name, error=str(exc))
                last_exc = exc

        raise RuntimeError(
            f"All providers failed for current price [{currency}]. Last error: {last_exc}"
        )

    async def get_historical(self, days: int, currency: str = "USD") -> list[HistoricalEntry]:
        order = self._historical_order.get(currency, [])
        last_exc: Exception | None = None

        for name in order:
            if name == "usd_conversion":
                try:
                    return await self._convert_historical_from_usd(days, currency)
                except Exception as exc:
                    logger.warning("usd_conversion_historical_failed", currency=currency, error=str(exc))
                    last_exc = exc
                continue

            provider = self._providers.get(name)
            if provider is None or not provider.supports_historical():
                logger.debug("provider_skipped", provider=name, reason="unsupported_or_missing")
                continue
            try:
                logger.info("provider_attempt_historical", provider=name, days=days, currency=currency)
                result = await self._fetch_with_retry(provider.get_historical, days)
                if result:
                    logger.info("provider_success_historical", provider=name, count=len(result))
                    return result
                raise ValueError(f"Provider {name} returned empty historical data")
            except Exception as exc:
                logger.warning("provider_failed_historical", provider=name, error=str(exc))
                last_exc = exc

        raise RuntimeError(
            f"All providers failed for historical data [{currency}]. Last error: {last_exc}"
        )

    # ------------------------------------------------------------------ #
    # USD conversion helpers
    # ------------------------------------------------------------------ #

    async def _get_usd_price(self) -> PriceResult:
        """Fetch a USD 24K price using the USD provider chain."""
        usd_order = self._currency_order.get("USD", [])
        last_exc: Exception | None = None
        for name in usd_order:
            if name == "usd_conversion":
                continue
            provider = self._providers.get(name)
            if provider is None or not provider.supports_current_price():
                continue
            try:
                result = await self._fetch_with_retry(provider.get_current_price)
                return result
            except Exception as exc:
                last_exc = exc
        raise RuntimeError(f"Could not obtain USD price for conversion. Last error: {last_exc}")

    async def _get_usd_historical(self, days: int) -> list[HistoricalEntry]:
        usd_order = self._historical_order.get("USD", [])
        last_exc: Exception | None = None
        for name in usd_order:
            if name == "usd_conversion":
                continue
            provider = self._providers.get(name)
            if provider is None or not provider.supports_historical():
                continue
            try:
                result = await self._fetch_with_retry(provider.get_historical, days)
                if result:
                    return result
            except Exception as exc:
                last_exc = exc
        raise RuntimeError(f"Could not obtain USD historical data for conversion. Last error: {last_exc}")

    async def _convert_from_usd(self, target_currency: str) -> PriceResult:
        usd_result = await self._get_usd_price()
        fx_rate = await self._fx.get_rate("USD", target_currency)

        converted_24k = round(usd_result.price * fx_rate, 4)
        carat_prices = derive_carat_prices(converted_24k)

        return PriceResult(
            price=converted_24k,
            currency=target_currency,
            carat="24K",
            source="usd_conversion",
            price_type="converted",
            date=usd_result.date,
            carat_prices=carat_prices,
            open=round(usd_result.open * fx_rate, 4) if usd_result.open else None,
            high=round(usd_result.high * fx_rate, 4) if usd_result.high else None,
            low=round(usd_result.low * fx_rate, 4) if usd_result.low else None,
        )

    async def _convert_historical_from_usd(self, days: int, target_currency: str) -> list[HistoricalEntry]:
        usd_entries = await self._get_usd_historical(days)
        fx_rate = await self._fx.get_rate("USD", target_currency)

        converted: list[HistoricalEntry] = []
        for e in usd_entries:
            converted.append(HistoricalEntry(
                date=e.date,
                price=round(e.price * fx_rate, 4),
                currency=target_currency,
                carat="24K",
                price_type="converted",
                calculated=False,
                source="usd_conversion",
                open=round(e.open * fx_rate, 4) if e.open else None,
                high=round(e.high * fx_rate, 4) if e.high else None,
                low=round(e.low * fx_rate, 4) if e.low else None,
            ))
        return converted

    # ------------------------------------------------------------------ #
    # Retry helper
    # ------------------------------------------------------------------ #

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
