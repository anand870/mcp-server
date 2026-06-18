from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GoldPriceResponse(BaseModel):
    price_usd: float
    currency: str = "USD"
    unit: str = "troy_oz"
    date: str
    source: str
    timestamp: str
    open_usd: float | None = None
    high_usd: float | None = None
    low_usd: float | None = None


class GoldHistoryEntry(BaseModel):
    date: str
    price_usd: float
    open_usd: float | None = None
    high_usd: float | None = None
    low_usd: float | None = None
    source: str


class GoldHistoryResponse(BaseModel):
    entries: list[GoldHistoryEntry]
    period_days: int
    start_date: str
    end_date: str
    count: int
    source: str = "database"


class GoldIndicatorsResponse(BaseModel):
    date: str
    price_usd: float
    ma7: float | None = None
    ma30: float | None = None
    ma90: float | None = None
    rsi14: float | None = None
    trend: str
    source: str = "calculated"


class ScoreBreakdown(BaseModel):
    price_below_ma30: int = Field(description="Points awarded if price < MA30")
    price_below_ma90: int = Field(description="Points awarded if price < MA90")
    rsi_below_35: int = Field(description="Points awarded if RSI < 35")
    ma7_above_ma30: int = Field(description="Points awarded if MA7 > MA30")
    total: int


class BuyOpportunityResponse(BaseModel):
    date: str
    price_usd: float
    score: int
    recommendation: str
    reasoning: list[str]
    score_breakdown: ScoreBreakdown
    indicators: GoldIndicatorsResponse
    confidence: float


class MarketSummaryResponse(BaseModel):
    text: str
    price_usd: float
    trend: str
    rsi14: float | None
    buy_score: int
    recommendation: str
    date: str
    source: str = "gold-advisor"


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    source: str = "gold-advisor"
