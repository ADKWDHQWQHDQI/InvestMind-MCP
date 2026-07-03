import logging
from src.mcp_server import mcp
from src.tools.ai_analysis import portfolio_risk, suggest_rebalancing
from src.tools.tax import tax_loss_harvesting
from src.tools.corp_actions import get_upcoming_actions
from src.tools.earnings import get_upcoming_results
from src.tools.watchlist import watchlist_summary
from src.tools.optimization import goal_based_plan

logger = logging.getLogger("investmind.tools.agents")

@mcp.tool()
async def portfolio_copilot(query: str) -> str:
    """
    Your comprehensive personal financial copilot agent. Answer complex portfolio queries.
    """
    risk = await portfolio_risk()
    reb = await suggest_rebalancing()
    return (
        f"**InvestMind Portfolio Copilot Response**\n"
        f"Regarding: '{query}'\n"
        f"- Active Portfolio Risk Category: {risk['risk_level']}\n"
        f"- Allocation Rebalance Status: {reb['status']}\n"
        f"We suggest monitoring concentration warnings and ensuring a balanced exposure profile."
    )

@mcp.tool()
async def market_research_agent(query: str) -> str:
    """
    Market research agent that crawls, aggregates, and summarizes stock news and indicators.
    """
    from src.tools.ai_chat import summarize_market
    market = await summarize_market()
    return f"**Market Research Agent Report**\n- Query: {query}\n- Current Status: {market}"

@mcp.tool()
async def dividend_agent() -> str:
    """
    Dividend agent tracking upcoming ex-dates and payout estimates.
    """
    actions = await get_upcoming_actions()
    divs = [a for a in actions if a["type"] == "Dividend"]
    if not divs:
        return "Dividend Agent: No upcoming ex-dividend dates detected in the portfolio watchlist."
    lines = [f"- **{d['symbol']}**: Rs. {d['amount']} (Ex-Date: {d['ex_date']})" for d in divs]
    return "Dividend Agent Report - Upcoming Dividends:\n" + "\n".join(lines)

@mcp.tool()
async def earnings_agent() -> str:
    """
    Earnings calendar tracking agent scanning for upcoming result dates.
    """
    results = await get_upcoming_results()
    lines = [f"- **{r['symbol']}**: Results date {r['earnings_date']} ({r['quarter']})" for r in results]
    return "Earnings Agent Report - Upcoming Releases:\n" + "\n".join(lines)

@mcp.tool()
async def portfolio_health_agent() -> str:
    """
    Health check agent reporting concentration, diversification, and rebalance triggers.
    """
    from src.tools.ai_analysis import diversification_score
    div = await diversification_score()
    reb = await suggest_rebalancing()
    return (
        f"**Portfolio Health Agent Report**\n"
        f"- Diversification Score: {div['diversification_score']}/100 ({div['rating']})\n"
        f"- Rebalancing Actions: {reb['status']}"
    )

@mcp.tool()
async def risk_agent() -> str:
    """
    Risk monitoring agent tracking stock betas and drawdown metrics.
    """
    risk = await portfolio_risk()
    return f"Risk Agent Report: Active portfolio risk level is evaluated as **{risk['risk_level']}**."

@mcp.tool()
def goal_agent(goal_amount: float, years: int) -> str:
    """
    Goal planning agent estimating monthly SIP requirements.
    """
    plan = goal_based_plan(goal_amount, years, 12.0)
    return (
        f"**Goal Agent Plan**\n"
        f"- Target Goal: Rs. {goal_amount}\n"
        f"- Horizon: {years} years\n"
        f"- Suggested Monthly SIP (assuming 12% CAGR): Rs. {plan['required_monthly_sip']}"
    )

@mcp.tool()
async def watchlist_agent() -> str:
    """
    Watchlist tracking agent alerting price swings inside watchlist groups.
    """
    summary = await watchlist_summary("default")
    if not summary.get("items"):
        return "Watchlist Agent: Your default watchlist is currently empty."
    lines = [f"- {item['symbol']}: Rs. {item['price']}" for item in summary["items"]]
    return "Watchlist Agent Price Summary:\n" + "\n".join(lines)

@mcp.tool()
async def tax_agent() -> str:
    """
    Tax optimization agent flagging LTCG exemptions and loss harvesting opportunities.
    """
    harvest = await tax_loss_harvesting()
    return (
        f"**Tax Optimization Agent Report**\n"
        f"- Total Harvestable Loss: Rs. {harvest.get('total_harvestable_loss', 0.0)}\n"
        f"- Harvesting Opportunities: {len(harvest.get('opportunities', []))} active recommendations."
    )
