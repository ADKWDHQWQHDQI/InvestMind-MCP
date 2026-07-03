import logging
import time
import os
from src.mcp_server import mcp

logger = logging.getLogger("investmind.tools.admin")

__version__ = "2.0.0"
_server_start_time = time.time()

@mcp.tool()
async def health() -> dict:
    """
    Returns the server operational health status with a live MongoDB ping.
    """
    db_status = "UNKNOWN"
    try:
        from src.database.connection import get_db
        db = await get_db()
        if db is not None:
            await db.command("ping")
            db_status = "CONNECTED"
        else:
            db_status = "DISCONNECTED"
    except Exception as e:
        db_status = f"ERROR: {e}"

    return {"status": "HEALTHY" if db_status == "CONNECTED" else "DEGRADED", "database": db_status}

@mcp.tool()
def metrics() -> dict:
    """
    Returns server resource usage, uptime, and active session count.
    """
    from src.security.auth import _active_sessions
    uptime = round(time.time() - _server_start_time, 1)
    return {
        "uptime_seconds": uptime,
        "active_sessions": len(_active_sessions),
        "env": os.environ.get("ENV", "development"),
        "pid": os.getpid()
    }

@mcp.tool()
def version() -> str:
    """
    Returns the server build and protocol version.
    """
    return f"InvestMind MCP Server version {__version__}"

@mcp.tool()
def usage() -> dict:
    """
    Returns API limits and active user request rates.
    """
    return {
        "message": "Rate limiting is not yet implemented. This tool will return usage statistics once rate limiting is configured."
    }

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
    return {
        "running": True,
        "mode": os.environ.get("ENV", "development"),
        "zero_knowledge_enforced": True,
        "version": __version__
    }

@mcp.tool()
def hello_mcp() -> str:
    """A hello tool to verify connectivity."""
    return "Hello! InvestMind MCP is working."
