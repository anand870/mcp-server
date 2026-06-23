from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.models import Base, GoldIndicator, GoldPrice, RecommendationHistory

_engine = None
_SessionLocal = None


def init_db() -> None:
    global _engine, _SessionLocal
    settings = get_settings()
    _engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    Base.metadata.create_all(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class GoldPriceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_latest(self, currency: str = "USD", carat: str = "24K") -> GoldPrice | None:
        return (
            self.session.query(GoldPrice)
            .filter_by(currency=currency, carat=carat)
            .order_by(GoldPrice.date.desc())
            .first()
        )

    def get_latest_date_for_currency(self, currency: str) -> str | None:
        row = (
            self.session.query(GoldPrice.date)
            .filter_by(currency=currency)
            .order_by(GoldPrice.date.desc())
            .first()
        )
        return row[0] if row else None

    def get_by_date_and_currency(self, date: str, currency: str) -> list[GoldPrice]:
        return (
            self.session.query(GoldPrice)
            .filter_by(date=date, currency=currency)
            .all()
        )

    def get_range(
        self, start_date: str, end_date: str, currency: str = "USD", carat: str = "24K"
    ) -> list[GoldPrice]:
        return (
            self.session.query(GoldPrice)
            .filter(
                GoldPrice.date >= start_date,
                GoldPrice.date <= end_date,
                GoldPrice.currency == currency,
                GoldPrice.carat == carat,
            )
            .order_by(GoldPrice.date.desc())
            .all()
        )

    def get_latest_per_currency_carat(self, currencies: list[str], carats: list[str]) -> list[GoldPrice]:
        """Return the single most-recent row for every (currency, carat) pair."""
        results = []
        for currency in currencies:
            latest_date = self.get_latest_date_for_currency(currency)
            if latest_date is None:
                continue
            rows = (
                self.session.query(GoldPrice)
                .filter(
                    GoldPrice.date == latest_date,
                    GoldPrice.currency == currency,
                    GoldPrice.carat.in_(carats),
                )
                .all()
            )
            results.extend(rows)
        return results


class GoldIndicatorRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_latest(self) -> GoldIndicator | None:
        return (
            self.session.query(GoldIndicator)
            .order_by(GoldIndicator.date.desc())
            .first()
        )


class RecommendationRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(
        self,
        date_str: str,
        price_usd: float,
        score: int,
        recommendation: str,
        reasoning: str,
        score_breakdown: dict,
    ) -> RecommendationHistory:
        record = RecommendationHistory(
            date=date_str,
            price_usd=price_usd,
            score=score,
            recommendation=recommendation,
            reasoning=reasoning,
            score_breakdown=json.dumps(score_breakdown),
        )
        self.session.add(record)
        return record

    def get_accuracy(self, horizon_days: int = 30) -> list[dict[str, Any]]:
        """Join recommendation_history with gold_prices to evaluate past recommendations."""
        sql = text("""
            SELECT
                r.date          AS rec_date,
                r.price_usd     AS price_at_rec,
                r.recommendation,
                r.score,
                p.price         AS outcome_price,
                p.date          AS outcome_date,
                ROUND(((p.price - r.price_usd) / r.price_usd * 100)::numeric, 2) AS return_pct,
                CASE
                    WHEN r.recommendation IN ('BUY', 'STRONG_BUY') AND p.price > r.price_usd THEN true
                    WHEN r.recommendation = 'AVOID'                AND p.price < r.price_usd THEN true
                    ELSE false
                END AS was_correct
            FROM recommendation_history r
            LEFT JOIN gold_prices p
                ON  p.currency = 'USD'
                AND p.carat    = '24K'
                AND p.date = (
                    SELECT MIN(p2.date)
                    FROM gold_prices p2
                    WHERE p2.currency = 'USD'
                      AND p2.carat    = '24K'
                      AND p2.date    >= (r.date::date + :horizon * INTERVAL '1 day')::text
                )
            WHERE r.date <= (CURRENT_DATE - :horizon * INTERVAL '1 day')::text
            ORDER BY r.date DESC
        """)
        rows = self.session.execute(sql, {"horizon": horizon_days}).mappings().all()
        return [dict(row) for row in rows]

    def count_pending(self, horizon_days: int = 30) -> int:
        """Count recommendations whose horizon has not yet elapsed."""
        sql = text("""
            SELECT COUNT(*) FROM recommendation_history
            WHERE date > (CURRENT_DATE - :horizon * INTERVAL '1 day')::text
        """)
        return self.session.execute(sql, {"horizon": horizon_days}).scalar() or 0
