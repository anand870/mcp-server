"""Live integration tests — hit real external APIs.

Run with:
    pytest -m live -v

Excluded from the default suite (no -m flag) because they require network
access and may be slow or rate-limited.
"""
from __future__ import annotations

import pytest


# ------------------------------------------------------------------ #
# iGold — AED live scraper
# ------------------------------------------------------------------ #

@pytest.mark.live
async def test_igold_live_price():
    from src.providers.currency.igold import IgoldProvider

    result = await IgoldProvider().get_current_price()

    assert result.currency == "AED"
    assert result.price_type == "local"
    assert result.source == "igold"
    # Sanity-check price is in a plausible AED per-gram range (150–700)
    assert 150 < result.price < 700, f"24K price out of expected range: {result.price}"

    carats = {cp.carat: cp for cp in result.carat_prices}
    assert set(carats) == {"24K", "22K", "21K", "18K"}, f"Missing carats: {set(carats)}"

    # All carats should be provider-supplied (scraped directly, not derived)
    for carat, cp in carats.items():
        assert cp.calculated is False, f"{carat} should not be calculated"
        assert cp.price > 0, f"{carat} price is zero or negative"

    # Purity ordering: 24K > 22K > 21K > 18K
    assert carats["24K"].price > carats["22K"].price > carats["21K"].price > carats["18K"].price


# ------------------------------------------------------------------ #
# Dubai City of Gold — AED live API
# ------------------------------------------------------------------ #

@pytest.mark.live
async def test_dcog_live_price():
    from src.providers.currency.dubaicityofgold import DubaiCityOfGoldProvider

    result = await DubaiCityOfGoldProvider().get_current_price()

    assert result.currency == "AED"
    assert result.price_type == "local"
    assert result.source == "dubaicityofgold"
    # Sanity-check price is in a plausible AED per-gram range (150–700)
    assert 150 < result.price < 700, f"24K price out of expected range: {result.price}"

    carats = {cp.carat: cp for cp in result.carat_prices}
    assert {"24K", "22K", "21K", "18K"}.issubset(set(carats)), f"Missing carats: {set(carats)}"
    assert carats["24K"].price > carats["18K"].price


@pytest.mark.live
async def test_igold_and_dcog_prices_are_close():
    """iGold and DCOG both source from Dubai gold market — prices should be within 2%."""
    from src.providers.currency.dubaicityofgold import DubaiCityOfGoldProvider
    from src.providers.currency.igold import IgoldProvider

    igold = await IgoldProvider().get_current_price()
    dcog = await DubaiCityOfGoldProvider().get_current_price()

    diff_pct = abs(igold.price - dcog.price) / dcog.price * 100
    assert diff_pct < 2.0, (
        f"iGold ({igold.price}) and DCOG ({dcog.price}) 24K prices diverge by {diff_pct:.2f}%"
    )


# ------------------------------------------------------------------ #
# Khaleej Times — INR live API
# ------------------------------------------------------------------ #

@pytest.mark.live
async def test_khaleejtimes_live_price():
    from src.providers.currency.khaleejtimes import KhaleejTimesProvider

    result = await KhaleejTimesProvider().get_current_price()

    assert result.currency == "INR"
    assert result.price_type == "local"
    assert result.source == "khaleejtimes"
    # Sanity-check: INR 24K per gram — broadly 9,000–25,000 range
    assert 9000 < result.price < 25000, f"24K INR/gram out of expected range: {result.price}"

    carats = {cp.carat: cp for cp in result.carat_prices}
    assert "24K" in carats and "22K" in carats and "18K" in carats
    assert carats["24K"].price > carats["22K"].price > carats["18K"].price
    assert carats["24K"].calculated is False


# ------------------------------------------------------------------ #
# FX rate provider — live exchange rates
# ------------------------------------------------------------------ #

@pytest.mark.live
async def test_fx_rate_usd_to_aed_live():
    from src.providers.fx_rates import FXRateProvider

    provider = FXRateProvider(cache_ttl_seconds=60)
    rate = await provider.get_rate("USD", "AED")

    # AED is pegged to USD at ~3.6725; allow ±0.05 drift
    assert 3.60 < rate < 3.75, f"USD/AED rate out of expected peg range: {rate}"


@pytest.mark.live
async def test_fx_rate_usd_to_inr_live():
    from src.providers.fx_rates import FXRateProvider

    provider = FXRateProvider(cache_ttl_seconds=60)
    rate = await provider.get_rate("USD", "INR")

    # INR floats; broad sanity range
    assert 70 < rate < 120, f"USD/INR rate out of expected range: {rate}"


# ------------------------------------------------------------------ #
# End-to-end: ProviderManager currency routing
# ------------------------------------------------------------------ #

@pytest.mark.live
async def test_manager_aed_routes_to_local_provider():
    from src.providers.manager import ProviderManager

    manager = ProviderManager()
    result = await manager.get_current_price(currency="AED")

    assert result.currency == "AED"
    assert result.source in ("igold", "dubaicityofgold"), (
        f"Expected a local AED provider, got: {result.source}"
    )
    assert result.price_type == "local"


@pytest.mark.live
async def test_manager_usd_price():
    from src.providers.manager import ProviderManager

    manager = ProviderManager()
    result = await manager.get_current_price(currency="USD")

    assert result.currency == "USD"
    # USD gold: broad sanity range per gram (~$107 at $3325/toz)
    assert 50 < result.price < 200, f"USD price out of expected range: {result.price}"
