from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.schemas import (
    BuyOpportunityResponse,
    GoldHistoryResponse,
    GoldIndicatorsResponse,
    GoldPriceResponse,
    MarketSummaryResponse,
    ScoreBreakdown,
)


def _make_price_response() -> GoldPriceResponse:
    return GoldPriceResponse(
        price_usd=3325.0,
        date="2024-06-17",
        source="freegoldapi",
        timestamp="2024-06-17T10:00:00Z",
    )


def _make_indicators_response() -> GoldIndicatorsResponse:
    return GoldIndicatorsResponse(
        date="2024-06-17",
        price_usd=3325.0,
        ma7=3300.0,
        ma30=3350.0,
        ma90=3400.0,
        rsi14=31.0,
        trend="Bullish",
    )


def _make_buy_response() -> BuyOpportunityResponse:
    ind = _make_indicators_response()
    return BuyOpportunityResponse(
        date="2024-06-17",
        price_usd=3325.0,
        score=78,
        recommendation="BUY",
        reasoning=[
            "Price $3325.00 is below MA30 $3350.00 (+40 pts)",
            "RSI(14) 31.0 is below 35 (oversold) (+20 pts)",
            "MA7 $3300.00 is below MA30 $3350.00 — momentum declining (+0 pts)",
        ],
        score_breakdown=ScoreBreakdown(
            price_below_ma30=40,
            price_below_ma90=0,
            rsi_below_35=20,
            ma7_above_ma30=0,
            total=60,
        ),
        indicators=ind,
        confidence=0.60,
    )


@pytest.mark.asyncio
async def test_get_gold_price_returns_dict():
    from src.tools.price_tools import get_gold_price

    with patch("src.tools.price_tools.GoldService") as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.get_current_price = AsyncMock(return_value=_make_price_response())
        result = await get_gold_price()

    assert isinstance(result, dict)
    assert result["price_usd"] == 3325.0
    assert result["source"] == "freegoldapi"


@pytest.mark.asyncio
async def test_get_gold_price_error_returns_error_dict():
    from src.tools.price_tools import get_gold_price

    with patch("src.tools.price_tools.GoldService") as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.get_current_price = AsyncMock(side_effect=RuntimeError("All providers failed"))
        result = await get_gold_price()

    assert "error" in result


@pytest.mark.asyncio
async def test_get_gold_history_valid_period():
    from src.tools.history_tools import get_gold_history

    mock_resp = GoldHistoryResponse(
        entries=[],
        period_days=90,
        start_date="2024-03-18",
        end_date="2024-06-17",
        count=0,
    )
    with patch("src.tools.history_tools.GoldService") as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.get_history = AsyncMock(return_value=mock_resp)
        result = await get_gold_history("90d")

    assert isinstance(result, dict)
    assert result["period_days"] == 90


@pytest.mark.asyncio
async def test_get_gold_history_invalid_period():
    from src.tools.history_tools import get_gold_history
    result = await get_gold_history("invalid")
    assert "error" in result


@pytest.mark.asyncio
async def test_get_gold_indicators_returns_dict():
    from src.tools.indicator_tools import get_gold_indicators

    with patch("src.tools.indicator_tools.IndicatorService") as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.get_latest_indicators.return_value = _make_indicators_response()
        result = await get_gold_indicators()

    assert isinstance(result, dict)
    assert result["rsi14"] == 31.0
    assert result["trend"] == "Bullish"


@pytest.mark.asyncio
async def test_analyze_buy_opportunity_returns_dict():
    from src.tools.analysis_tools import analyze_buy_opportunity

    with patch("src.tools.analysis_tools.RecommendationService") as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.analyze_buy_opportunity = AsyncMock(return_value=_make_buy_response())
        result = await analyze_buy_opportunity()

    assert isinstance(result, dict)
    assert result["recommendation"] == "BUY"
    assert result["score"] == 78
    assert "reasoning" in result
    assert "score_breakdown" in result


@pytest.mark.asyncio
async def test_get_market_summary_text_format():
    from src.tools.summary_tools import get_market_summary

    with patch("src.tools.summary_tools.RecommendationService") as mock_svc_cls:
        mock_svc = mock_svc_cls.return_value
        mock_svc.analyze_buy_opportunity = AsyncMock(return_value=_make_buy_response())
        result = await get_market_summary()

    assert isinstance(result, dict)
    assert "text" in result
    text = result["text"]
    assert "Gold Price:" in text
    assert "Trend:" in text
    assert "RSI:" in text
    assert "Buy Score:" in text
    assert "Recommendation:" in text
    assert result["recommendation"] == "BUY"
