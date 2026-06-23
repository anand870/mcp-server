from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.schemas import (
    BuyOpportunityResponse,
    CaratPriceDetail,
    GoldHistoryResponse,
    GoldIndicatorsResponse,
    GoldPriceResponse,
    ScoreBreakdown,
)


def _make_price_response(currency: str = "AED", carat: str = "24K") -> GoldPriceResponse:
    return GoldPriceResponse(
        price=509.30,
        currency=currency,
        carat=carat,
        price_type="local",
        date="2024-06-17",
        source="igold",
        timestamp="2024-06-17T10:00:00Z",
        all_carats=[
            CaratPriceDetail(carat="24K", price=509.30, calculated=False),
            CaratPriceDetail(carat="22K", price=471.54, calculated=False),
            CaratPriceDetail(carat="21K", price=450.09, calculated=False),
            CaratPriceDetail(carat="18K", price=385.79, calculated=False),
        ],
    )


def _make_indicators_response() -> GoldIndicatorsResponse:
    return GoldIndicatorsResponse(
        date="2024-06-17",
        price_usd_gram=106.89,
        ma7=106.0,
        ma30=107.7,
        ma90=109.3,
        rsi14=31.0,
        trend="Bullish",
    )


def _make_buy_response() -> BuyOpportunityResponse:
    return BuyOpportunityResponse(
        date="2024-06-17",
        price=509.30,
        currency="AED",
        carat="24K",
        price_usd_gram=106.89,
        score=78,
        recommendation="BUY",
        reasoning=[
            "USD price $106.8900/g is below MA30 $107.7000/g (+40 pts)",
            "RSI(14) 31.0 is below 35 (oversold) (+20 pts)",
        ],
        score_breakdown=ScoreBreakdown(
            price_below_ma30=40,
            price_below_ma90=0,
            rsi_below_35=20,
            ma7_above_ma30=0,
            total=60,
        ),
        indicators=_make_indicators_response(),
        confidence=0.60,
    )


@pytest.mark.asyncio
async def test_get_gold_price_returns_dict():
    from src.tools.price_tools import get_gold_price

    with patch("src.tools.price_tools.GoldService") as mock_cls:
        mock_cls.return_value.get_current_price = AsyncMock(return_value=_make_price_response())
        result = await get_gold_price(currency="AED", carat="24K")

    assert isinstance(result, dict)
    assert result["price"] == 509.30
    assert result["currency"] == "AED"
    assert result["carat"] == "24K"
    assert result["price_type"] == "local"
    assert result["source"] == "igold"


@pytest.mark.asyncio
async def test_get_gold_price_defaults():
    from src.tools.price_tools import get_gold_price

    with patch("src.tools.price_tools.GoldService") as mock_cls:
        mock_cls.return_value.get_current_price = AsyncMock(return_value=_make_price_response())
        result = await get_gold_price()

    assert isinstance(result, dict)
    assert "price" in result


@pytest.mark.asyncio
async def test_get_gold_price_error_returns_error_dict():
    from src.tools.price_tools import get_gold_price

    with patch("src.tools.price_tools.GoldService") as mock_cls:
        mock_cls.return_value.get_current_price = AsyncMock(side_effect=RuntimeError("All providers failed"))
        result = await get_gold_price()

    assert "error" in result


@pytest.mark.asyncio
async def test_get_gold_prices_returns_nested_dict():
    from src.tools.prices_tools import get_gold_prices

    mock_prices = {
        "AED": {
            "24K": CaratPriceDetail(carat="24K", price=509.30, calculated=False),
            "22K": CaratPriceDetail(carat="22K", price=471.54, calculated=False),
        },
        "USD": {
            "24K": CaratPriceDetail(carat="24K", price=3325.0, calculated=False),
        },
    }
    with patch("src.tools.prices_tools.GoldService") as mock_cls:
        mock_cls.return_value.get_all_current_prices = AsyncMock(return_value=mock_prices)
        result = await get_gold_prices()

    assert isinstance(result, dict)
    assert "AED" in result
    assert "22K" in result["AED"]
    assert result["AED"]["22K"]["price"] == 471.54
    assert result["AED"]["22K"]["calculated"] is False


@pytest.mark.asyncio
async def test_get_gold_history_valid_period():
    from src.tools.history_tools import get_gold_history

    mock_resp = GoldHistoryResponse(
        entries=[],
        period_days=90,
        start_date="2024-03-18",
        end_date="2024-06-17",
        count=0,
        currency="AED",
        carat="24K",
    )
    with patch("src.tools.history_tools.GoldService") as mock_cls:
        mock_cls.return_value.get_history = AsyncMock(return_value=mock_resp)
        result = await get_gold_history("90d", currency="AED", carat="24K")

    assert isinstance(result, dict)
    assert result["period_days"] == 90
    assert result["currency"] == "AED"


@pytest.mark.asyncio
async def test_get_gold_history_invalid_period():
    from src.tools.history_tools import get_gold_history
    result = await get_gold_history("invalid")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_gold_indicators_returns_dict():
    from src.tools.indicator_tools import get_gold_indicators

    with patch("src.tools.indicator_tools.IndicatorService") as mock_cls:
        mock_cls.return_value.get_latest_indicators.return_value = _make_indicators_response()
        result = await get_gold_indicators()

    assert isinstance(result, dict)
    assert result["rsi14"] == 31.0
    assert result["trend"] == "Bullish"


@pytest.mark.asyncio
async def test_analyze_buy_opportunity_with_currency():
    from src.tools.analysis_tools import analyze_buy_opportunity

    with patch("src.tools.analysis_tools.RecommendationService") as mock_cls:
        mock_cls.return_value.analyze_buy_opportunity = AsyncMock(return_value=_make_buy_response())
        result = await analyze_buy_opportunity(currency="AED", carat="24K")

    assert isinstance(result, dict)
    assert result["recommendation"] == "BUY"
    assert result["score"] == 78
    assert result["currency"] == "AED"
    assert result["price_usd_gram"] == 106.89
    assert "reasoning" in result
    assert "score_breakdown" in result


@pytest.mark.asyncio
async def test_get_market_summary_text_format():
    from src.tools.summary_tools import get_market_summary

    mock_prices = {
        "AED": {
            "24K": CaratPriceDetail(carat="24K", price=509.30, calculated=False),
            "22K": CaratPriceDetail(carat="22K", price=471.54, calculated=False),
        },
        "USD": {
            "24K": CaratPriceDetail(carat="24K", price=3325.0, calculated=False),
        },
    }
    with (
        patch("src.tools.summary_tools.GoldService") as mock_gold_cls,
        patch("src.tools.summary_tools.RecommendationService") as mock_rec_cls,
    ):
        mock_gold_cls.return_value.get_all_current_prices = AsyncMock(return_value=mock_prices)
        mock_rec_cls.return_value.analyze_buy_opportunity = AsyncMock(return_value=_make_buy_response())
        result = await get_market_summary()

    assert isinstance(result, dict)
    assert "text" in result
    text = result["text"]
    assert "Gold Prices" in text
    assert "AED" in text
    assert "USD" in text
    assert "Buy Score" in text
    assert "Recommendation" in text
    assert result["recommendation"] == "BUY"
