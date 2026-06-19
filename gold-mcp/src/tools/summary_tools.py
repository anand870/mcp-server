from __future__ import annotations

from src.schemas import CaratPriceDetail, MarketSummaryResponse
from src.services.gold_service import GoldService
from src.services.recommendation_service import RecommendationService
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _price_label(detail: CaratPriceDetail) -> str:
    suffix = " [calc]" if detail.calculated else ""
    return f"{detail.price:,.2f}{suffix}"


async def get_market_summary() -> dict:
    """
    Return a concise market summary for all configured currencies, suitable for Telegram.

    Shows provider, price_type (local/converted), and calculated vs provider-supplied carats.
    Buy score is always based on USD 24K technical indicators.
    """
    logger.info("tool_invoked", tool="get_market_summary")
    try:
        gold_svc = GoldService()
        rec_svc = RecommendationService()

        all_prices = await gold_svc.get_all_current_prices()
        analysis = await rec_svc.analyze_buy_opportunity(currency="USD", carat="24K")

        lines: list[str] = ["Gold Prices", ""]

        for currency, carats in all_prices.items():
            if not carats:
                lines.append(f"{currency}: unavailable")
                lines.append("")
                continue

            lines.append(f"{currency}")
            for carat_label, detail in sorted(carats.items()):
                lines.append(f"  {carat_label}: {_price_label(detail)}")
            lines.append("")

        rsi = analysis.indicators.rsi14
        rsi_str = f"{rsi:.0f}" if rsi is not None else "N/A"
        lines += [
            f"Buy Score (USD 24K basis)",
            f"  Score: {analysis.score}/100",
            f"  Trend: {analysis.indicators.trend}",
            f"  RSI: {rsi_str}",
            f"  Recommendation: {analysis.recommendation}",
        ]

        text = "\n".join(lines)

        summary = MarketSummaryResponse(
            text=text,
            prices={
                currency: {carat: detail for carat, detail in carats.items()}
                for currency, carats in all_prices.items()
            },
            buy_score=analysis.score,
            recommendation=analysis.recommendation,
            trend=analysis.indicators.trend,
            rsi14=rsi,
            date=analysis.date,
        )
        return summary.model_dump()
    except Exception as exc:
        logger.error("tool_error", tool="get_market_summary", error=str(exc))
        return {"error": str(exc), "source": "gold-advisor"}
