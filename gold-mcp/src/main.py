from __future__ import annotations

import os
import sys
from pathlib import Path

# Anchor to project root so all relative paths (config.yaml, data/gold.db)
# resolve correctly regardless of the working directory Hermes or any MCP
# client uses when spawning this process.
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


@mcp.tool(description="Fetch the current gold spot price in USD per troy ounce from the best available provider.")
async def tool_get_gold_price() -> dict:
    return await get_gold_price()


@mcp.tool(description=(
    "Fetch historical gold prices for a given period. "
    "period must be one of: 30d, 90d, 1y, 5y, 10y."
))
async def tool_get_gold_history(period: str = "90d") -> dict:
    return await get_gold_history(period)


@mcp.tool(description=(
    "Return the latest computed technical indicators for gold: "
    "MA7, MA30, MA90, RSI(14), and trend direction."
))
async def tool_get_gold_indicators() -> dict:
    return await get_gold_indicators()


@mcp.tool(description=(
    "Analyze whether now is a good time to buy gold. "
    "Returns a score (0-100), recommendation (AVOID/WAIT/BUY/STRONG_BUY), "
    "and detailed reasoning for each scoring component."
))
async def tool_analyze_buy_opportunity() -> dict:
    return await analyze_buy_opportunity()


@mcp.tool(description=(
    "Return a concise market summary suitable for Telegram or AI agent chat. "
    "Includes gold price, trend, RSI, buy score, and recommendation."
))
async def tool_get_market_summary() -> dict:
    return await get_market_summary()


if __name__ == "__main__":
    logger.info("gold_advisor_mcp_starting", name=config.server.name, version=config.server.version)
    mcp.run()
