from __future__ import annotations

from src.config import get_config
from src.database import RecommendationRepository, session_scope
from src.schemas import BuyOpportunityResponse, ScoreBreakdown
from src.services.gold_service import GoldService
from src.services.indicator_service import IndicatorService
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _map_recommendation(score: int, thresholds) -> str:
    if score <= thresholds.avoid_max:
        return "AVOID"
    if score <= thresholds.wait_max:
        return "WAIT"
    if score <= thresholds.buy_max:
        return "BUY"
    return "STRONG_BUY"


class RecommendationService:
    def __init__(self):
        self._gold_svc = GoldService()
        self._ind_svc = IndicatorService()

    async def analyze_buy_opportunity(
        self, currency: str | None = None, carat: str | None = None
    ) -> BuyOpportunityResponse:
        config = get_config()
        rules = config.scoring.rules
        thresholds = config.scoring.thresholds

        # Price in the requested currency/carat (for display)
        price_resp = await self._gold_svc.get_current_price(currency=currency, carat=carat)

        # Indicators and scoring always use USD 24K
        usd_price_resp = await self._gold_svc.get_current_price(currency="USD", carat="24K")
        indicators = self._ind_svc.get_latest_indicators()

        if indicators is None:
            raise RuntimeError("No indicators available. Run scripts/refresh_history.py first.")

        usd_price = usd_price_resp.price
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
            breakdown.price_below_ma30 = rules.price_below_ma30
            reasoning.append(f"USD price ${usd_price:.4f}/g is below MA30 ${ma30:.4f}/g (+{rules.price_below_ma30} pts)")
        elif ma30 is not None:
            reasoning.append(f"USD price ${usd_price:.4f}/g is above MA30 ${ma30:.4f}/g (+0 pts)")

        if ma90 is not None and usd_price < ma90:
            breakdown.price_below_ma90 = rules.price_below_ma90
            reasoning.append(f"USD price ${usd_price:.4f}/g is below MA90 ${ma90:.4f}/g (+{rules.price_below_ma90} pts)")
        elif ma90 is not None:
            reasoning.append(f"USD price ${usd_price:.4f}/g is above MA90 ${ma90:.4f}/g (+0 pts)")

        if rsi14 is not None and rsi14 < 35:
            breakdown.rsi_below_35 = rules.rsi_below_35
            reasoning.append(f"RSI(14) {rsi14:.1f} is below 35 (oversold) (+{rules.rsi_below_35} pts)")
        elif rsi14 is not None:
            reasoning.append(f"RSI(14) {rsi14:.1f} is not oversold (+0 pts)")

        if ma7 is not None and ma30 is not None and ma7 > ma30:
            breakdown.ma7_above_ma30 = rules.ma7_above_ma30
            reasoning.append(f"MA7 ${ma7:.4f}/g is above MA30 ${ma30:.4f}/g — momentum rising (+{rules.ma7_above_ma30} pts)")
        elif ma7 is not None and ma30 is not None:
            reasoning.append(f"MA7 ${ma7:.4f}/g is below MA30 ${ma30:.4f}/g — momentum declining (+0 pts)")

        score = (
            breakdown.price_below_ma30
            + breakdown.price_below_ma90
            + breakdown.rsi_below_35
            + breakdown.ma7_above_ma30
        )
        breakdown.total = score
        recommendation = _map_recommendation(score, thresholds)

        max_possible = (
            rules.price_below_ma30
            + rules.price_below_ma90
            + rules.rsi_below_35
            + rules.ma7_above_ma30
        )
        confidence = score / max_possible if max_possible > 0 else 0.0

        with session_scope() as session:
            repo = RecommendationRepository(session)
            repo.save(
                date_str=price_resp.date,
                price_usd=usd_price,
                score=score,
                recommendation=recommendation,
                reasoning="; ".join(reasoning),
                score_breakdown=breakdown.model_dump(),
            )

        logger.info(
            "recommendation_generated",
            score=score,
            recommendation=recommendation,
            price=price_resp.price,
            currency=price_resp.currency,
            carat=price_resp.carat,
        )

        return BuyOpportunityResponse(
            date=price_resp.date,
            price=price_resp.price,
            currency=price_resp.currency,
            carat=price_resp.carat,
            price_usd_gram=usd_price,
            score=score,
            recommendation=recommendation,
            reasoning=reasoning,
            score_breakdown=breakdown,
            indicators=indicators,
            confidence=round(confidence, 2),
        )
