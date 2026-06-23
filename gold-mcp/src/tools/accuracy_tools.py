from __future__ import annotations

from src.database import RecommendationRepository, session_scope
from src.schemas import (
    AccuracyByType,
    RecommendationAccuracyEntry,
    RecommendationAccuracyResponse,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

_DIRECTIONAL = {"BUY", "STRONG_BUY", "AVOID"}


def get_recommendation_accuracy(horizon_days: int = 30) -> dict:
    logger.info("get_recommendation_accuracy", horizon_days=horizon_days)
    with session_scope() as session:
        repo = RecommendationRepository(session)
        rows = repo.get_accuracy(horizon_days)
        pending_count = repo.count_pending(horizon_days)

    entries: list[RecommendationAccuracyEntry] = []
    by_type: dict[str, dict] = {}

    for row in rows:
        entry = RecommendationAccuracyEntry(
            rec_date=row["rec_date"],
            price_at_rec=float(row["price_at_rec"]),
            recommendation=row["recommendation"],
            score=row["score"],
            outcome_price=float(row["outcome_price"]) if row["outcome_price"] is not None else None,
            outcome_date=row["outcome_date"],
            return_pct=float(row["return_pct"]) if row["return_pct"] is not None else None,
            was_correct=row["was_correct"] if row["recommendation"] in _DIRECTIONAL else None,
        )
        entries.append(entry)

        rec = row["recommendation"]
        bucket = by_type.setdefault(rec, {"count": 0, "correct": 0, "returns": []})
        bucket["count"] += 1
        if row["was_correct"] and rec in _DIRECTIONAL:
            bucket["correct"] += 1
        if row["return_pct"] is not None:
            bucket["returns"].append(float(row["return_pct"]))

    by_recommendation: dict[str, AccuracyByType] = {}
    for rec, b in by_type.items():
        hit_rate = (b["correct"] / b["count"]) if b["count"] > 0 and rec in _DIRECTIONAL else None
        avg_ret = (sum(b["returns"]) / len(b["returns"])) if b["returns"] else None
        by_recommendation[rec] = AccuracyByType(
            count=b["count"],
            correct=b["correct"],
            hit_rate=round(hit_rate, 4) if hit_rate is not None else None,
            avg_return_pct=round(avg_ret, 4) if avg_ret is not None else None,
        )

    directional_entries = [e for e in entries if e.recommendation in _DIRECTIONAL and e.was_correct is not None]
    overall_hit_rate = (
        round(sum(1 for e in directional_entries if e.was_correct) / len(directional_entries), 4)
        if directional_entries else None
    )

    buy_entries = [e for e in entries if e.recommendation in {"BUY", "STRONG_BUY"} and e.return_pct is not None]
    avg_return_pct = (
        round(sum(e.return_pct for e in buy_entries) / len(buy_entries), 4)
        if buy_entries else None
    )

    return RecommendationAccuracyResponse(
        horizon_days=horizon_days,
        evaluated_count=len(entries),
        pending_count=pending_count,
        overall_hit_rate=overall_hit_rate,
        avg_return_pct=avg_return_pct,
        by_recommendation=by_recommendation,
        entries=entries,
    ).model_dump()
