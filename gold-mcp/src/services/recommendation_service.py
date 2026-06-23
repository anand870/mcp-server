from __future__ import annotations

from src.config import get_settings
from src.database import GoldPriceRepository, RecommendationRepository, session_scope
from src.schemas import BuyOpportunityResponse, ScoreBreakdown
from src.services.indicator_service import get_latest_indicators


def _map_recommendation(score: int) -> str:
    if score <= 30:
        return "AVOID"
    if score <= 60:
        return "WAIT"
    if score <= 80:
        return "BUY"
    return "STRONG_BUY"


def analyze_buy_opportunity(currency: str = "AED", carat: str = "24K") -> BuyOpportunityResponse:
    settings = get_settings()

    indicators = get_latest_indicators()
    if indicators is None:
        raise RuntimeError("No indicators available in the database.")

    with session_scope() as session:
        price_repo = GoldPriceRepository(session)
        display_price_row = price_repo.get_latest(currency=currency, carat=carat)
        usd_price_row = price_repo.get_latest(currency="USD", carat="24K")

    if usd_price_row is None:
        raise RuntimeError("No USD 24K price found in database.")

    usd_price = usd_price_row.price
    display_price = display_price_row.price if display_price_row else usd_price
    display_date = display_price_row.date if display_price_row else usd_price_row.date
    display_source = display_price_row.source if display_price_row else usd_price_row.source
    display_price_type = display_price_row.price_type if display_price_row else "converted"

    ma30 = indicators.ma30
    ma90 = indicators.ma90
    rsi14 = indicators.rsi14
    ma7 = indicators.ma7

    breakdown = ScoreBreakdown(
        price_below_ma30=0,
        price_below_ma90=0,
        rsi_below_35=0,
        ma7_above_ma30=0,
        total=0,
    )
    reasoning: list[str] = []

    if ma30 is not None and usd_price < ma30:
        breakdown.price_below_ma30 = settings.scoring_price_below_ma30
        reasoning.append(f"USD price ${usd_price:.4f}/g is below MA30 ${ma30:.4f}/g (+{settings.scoring_price_below_ma30} pts)")
    elif ma30 is not None:
        reasoning.append(f"USD price ${usd_price:.4f}/g is above MA30 ${ma30:.4f}/g (+0 pts)")

    if ma90 is not None and usd_price < ma90:
        breakdown.price_below_ma90 = settings.scoring_price_below_ma90
        reasoning.append(f"USD price ${usd_price:.4f}/g is below MA90 ${ma90:.4f}/g (+{settings.scoring_price_below_ma90} pts)")
    elif ma90 is not None:
        reasoning.append(f"USD price ${usd_price:.4f}/g is above MA90 ${ma90:.4f}/g (+0 pts)")

    if rsi14 is not None and rsi14 < 35:
        breakdown.rsi_below_35 = settings.scoring_rsi_below_35
        reasoning.append(f"RSI(14) {rsi14:.1f} is below 35 (oversold) (+{settings.scoring_rsi_below_35} pts)")
    elif rsi14 is not None:
        reasoning.append(f"RSI(14) {rsi14:.1f} is not oversold (+0 pts)")

    if ma7 is not None and ma30 is not None and ma7 > ma30:
        breakdown.ma7_above_ma30 = settings.scoring_ma7_above_ma30
        reasoning.append(f"MA7 ${ma7:.4f}/g is above MA30 ${ma30:.4f}/g — momentum rising (+{settings.scoring_ma7_above_ma30} pts)")
    elif ma7 is not None and ma30 is not None:
        reasoning.append(f"MA7 ${ma7:.4f}/g is below MA30 ${ma30:.4f}/g — momentum declining (+0 pts)")

    score = (
        breakdown.price_below_ma30
        + breakdown.price_below_ma90
        + breakdown.rsi_below_35
        + breakdown.ma7_above_ma30
    )
    breakdown.total = score
    recommendation = _map_recommendation(score)

    max_possible = (
        settings.scoring_price_below_ma30
        + settings.scoring_price_below_ma90
        + settings.scoring_rsi_below_35
        + settings.scoring_ma7_above_ma30
    )
    confidence = round(score / max_possible, 2) if max_possible > 0 else 0.0

    with session_scope() as session:
        repo = RecommendationRepository(session)
        repo.save(
            date_str=display_date,
            price_usd=usd_price,
            score=score,
            recommendation=recommendation,
            reasoning="; ".join(reasoning),
            score_breakdown=breakdown.model_dump(),
        )

    return BuyOpportunityResponse(
        date=display_date,
        price=display_price,
        currency=currency,
        carat=carat,
        price_usd_gram=usd_price,
        score=score,
        recommendation=recommendation,
        reasoning=reasoning,
        score_breakdown=breakdown,
        indicators=indicators,
        confidence=confidence,
    )
