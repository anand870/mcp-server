from __future__ import annotations

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent.resolve()
os.chdir(_PROJECT_ROOT)
sys.path.insert(0, str(_PROJECT_ROOT))

from fastmcp import FastMCP

from src.config import get_config
from src.database import init_db
from src.tools.analysis_tools import analyze_buy_opportunity
from src.tools.history_tools import get_gold_history
from src.tools.indicator_tools import get_gold_indicators
from src.tools.price_tools import get_gold_price
from src.tools.prices_tools import get_gold_prices
from src.tools.summary_tools import get_market_summary
from src.utils.logging import configure_logging, get_logger

config = get_config()
configure_logging(
    level=config.logging.level,
    fmt=config.logging.format,
    log_file=config.logging.log_file,
    max_bytes=config.logging.log_file_max_bytes,
    backup_count=config.logging.log_file_backup_count,
)
logger = get_logger(__name__)

init_db()

mcp = FastMCP(
    name=config.server.name,
    instructions=config.server.description,
)


@mcp.tool(description=(
    "Fetch the current gold price for the given currency and carat. "
    "currency: USD, AED, INR (default: configured default_currency). "
    "carat: 24K, 22K, 21K, 18K (default: configured default_carat)."
))
async def tool_get_gold_price(currency: str = "", carat: str = "") -> dict:
    return await get_gold_price(currency=currency or None, carat=carat or None)


@mcp.tool(description=(
    "Fetch current gold prices for all enabled currencies and all standard carats (24K/22K/21K/18K). "
    "Returns a nested dict: {currency: {carat: {price, calculated}}}."
))
async def tool_get_gold_prices() -> dict:
    return await get_gold_prices()


@mcp.tool(description=(
    "Fetch historical gold prices for a given period and currency/carat. "
    "period: 30d, 90d, 1y, 5y, 10y. "
    "currency: USD, AED, INR. carat: 24K, 22K, 21K, 18K."
))
async def tool_get_gold_history(period: str = "90d", currency: str = "", carat: str = "") -> dict:
    return await get_gold_history(period, currency=currency or None, carat=carat or None)


@mcp.tool(description=(
    "Return the latest computed technical indicators for gold (USD 24K basis): "
    "MA7, MA30, MA90, RSI(14), and trend direction."
))
async def tool_get_gold_indicators() -> dict:
    return await get_gold_indicators()


@mcp.tool(description=(
    "Analyze whether now is a good time to buy gold. "
    "Score (0-100) is always based on USD 24K indicators. "
    "Price in response reflects the requested currency/carat. "
    "currency: USD, AED, INR. carat: 24K, 22K, 21K, 18K."
))
async def tool_analyze_buy_opportunity(currency: str = "", carat: str = "") -> dict:
    return await analyze_buy_opportunity(currency=currency or None, carat=carat or None)


@mcp.tool(description=(
    "Return a concise market summary for all configured currencies, "
    "suitable for Telegram or AI agent chat. "
    "Shows prices, provider source, and buy recommendation."
))
async def tool_get_market_summary() -> dict:
    return await get_market_summary()


def _run_http() -> None:
    import uvicorn
    from src.http_server import app
    logger.info("gold_advisor_http_starting", host=config.http.host, port=config.http.port)
    uvicorn.run(app, host=config.http.host, port=config.http.port)


def _run_mcp() -> None:
    logger.info("gold_advisor_mcp_starting", name=config.server.name, version=config.server.version)
    mcp.run()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Gold Advisor server")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--http", action="store_true", help="Run as HTTP REST server")
    group.add_argument("--all", action="store_true", help="Run both MCP (stdio) and HTTP concurrently")
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
