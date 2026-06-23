from __future__ import annotations

import os
import sys
from pathlib import Path

# Anchor CWD to project root so relative paths (data/, .env) resolve correctly
# regardless of where the MCP client launches this process from.
os.chdir(Path(__file__).parent.parent.resolve())
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from src.utils.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

from fastmcp import FastMCP

from src.database import init_db
from src.tools.accuracy_tools import get_recommendation_accuracy
from src.tools.analysis_tools import analyze_buy_opportunity, get_gold_indicators
from src.tools.history_tools import get_gold_history
from src.tools.price_tools import get_gold_price, get_gold_prices
from src.tools.summary_tools import get_market_summary

init_db()
logger.info("gold_advisor_v2_db_initialized")

mcp = FastMCP(
    name="gold-advisor-v2",
    instructions=(
        "Read-only MCP server for gold price data, historical trends, "
        "technical indicators (MA7/MA30/MA90/RSI14), and buy recommendations. "
        "All data is read from a shared PostgreSQL database."
    ),
)


@mcp.tool(description=(
    "Fetch the current gold price for a given currency and carat. "
    "Returns the price for the requested carat plus all other carats on the same date. "
    "currency: USD, AED, INR (default: AED). carat: 24K, 22K, 21K, 18K (default: 24K)."
))
def tool_get_gold_price(currency: str = "AED", carat: str = "24K") -> dict:
    return get_gold_price(currency=currency, carat=carat)


@mcp.tool(description=(
    "Fetch latest gold prices for all currencies (USD, AED, INR) "
    "and all carats (24K, 22K, 21K, 18K). "
    "Returns a nested dict: {currency: {carat: {price, calculated, source, date}}}."
))
def tool_get_gold_prices() -> dict:
    return get_gold_prices()


@mcp.tool(description=(
    "Fetch historical gold prices for a given period. "
    "period: 30d, 90d, 1y, 5y, 10y (default: 30d). "
    "currency: USD, AED, INR (default: USD). carat: 24K, 22K, 21K, 18K (default: 24K)."
))
def tool_get_gold_history(period: str = "30d", currency: str = "USD", carat: str = "24K") -> dict:
    return get_gold_history(period=period, currency=currency, carat=carat)


@mcp.tool(description=(
    "Return the latest computed technical indicators for gold (USD 24K basis): "
    "MA7, MA30, MA90, RSI(14), and trend direction."
))
def tool_get_gold_indicators() -> dict:
    return get_gold_indicators()


@mcp.tool(description=(
    "Analyze whether now is a good time to buy gold. "
    "Score (0-100) based on USD 24K indicators. "
    "Display price reflects the requested currency/carat. "
    "Saves the result to recommendation_history. "
    "currency: USD, AED, INR (default: AED). carat: 24K, 22K, 21K, 18K (default: 24K)."
))
def tool_analyze_buy_opportunity(currency: str = "AED", carat: str = "24K") -> dict:
    return analyze_buy_opportunity(currency=currency, carat=carat)


@mcp.tool(description=(
    "Return a concise market summary for all currencies, "
    "suitable for Telegram or AI agent chat. "
    "Includes latest prices, current indicators, and buy recommendation."
))
def tool_get_market_summary() -> dict:
    return get_market_summary()


@mcp.tool(description=(
    "Evaluate the accuracy of past buy/avoid recommendations by comparing "
    "the price at recommendation time against the actual price after horizon_days. "
    "Returns per-type hit rates, average return for BUY/STRONG_BUY signals, "
    "and a full entry list. horizon_days: lookback horizon in days (default: 30)."
))
def tool_get_recommendation_accuracy(horizon_days: int = 30) -> dict:
    return get_recommendation_accuracy(horizon_days=horizon_days)


def _run_http() -> None:
    import uvicorn
    from src.http_server import app
    logger.info("gold_advisor_v2_http_starting", host="0.0.0.0", port=8080)
    uvicorn.run(app, host="0.0.0.0", port=8080)


def _run_mcp() -> None:
    logger.info("gold_advisor_v2_mcp_starting")
    mcp.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gold Advisor v2 server")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--http", action="store_true", help="Run HTTP REST server only (with Swagger at /docs)")
    group.add_argument("--all", action="store_true", help="Run MCP (stdio) + HTTP concurrently")
    args = parser.parse_args()

    if args.http:
        _run_http()
    elif args.all:
        import threading
        http_thread = threading.Thread(target=_run_http, daemon=True)
        http_thread.start()
        _run_mcp()
    else:
        _run_mcp()
