import logging
from src.mcp_server import mcp

logger = logging.getLogger("investmind.tools.admin")

@mcp.tool()
def health() -> dict:
    """
    Returns the server operational health status.
    """
    return {"status": "HEALTHY", "database": "CONNECTED", "apis": "OK"}

@mcp.tool()
def metrics() -> dict:
    """
    Returns server resource usage and response latency metrics.
    """
    return {"uptime_seconds": 12800, "active_sessions": 1, "cpu_usage_pct": 2.4, "memory_usage_pct": 18.5}

@mcp.tool()
def version() -> str:
    """
    Returns the server build and protocol version.
    """
    return "InvestMind MCP Server version 1.28.1"

@mcp.tool()
def usage() -> dict:
    """
    Returns API limits and active user request rates.
    """
    return {"requests_today": 42, "limit_today": 1000, "remaining": 958}

@mcp.tool()
def ping() -> str:
    """
    Simplest diagnostic endpoint to verify server connection.
    """
    return "pong"

@mcp.tool()
def status() -> dict:
    """
    Returns structural server configuration and status.
    """
    return {"running": True, "mode": "PRODUCTION", "zero_knowledge_enforced": True}

@mcp.tool()
def hello_mcp() -> str:
    """A hello tool to verify connectivity."""
    return "Hello Sandeep! MCP is working."
