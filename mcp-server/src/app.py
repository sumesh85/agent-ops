"""
Singleton FastMCP instance.

Imported by tool modules (which register @mcp.tool() decorators)
and by server.py (which runs it).
"""

from mcp.server.fastmcp import FastMCP
from src.config import settings

mcp = FastMCP(
    name="agentops-investigation-tools",
    instructions=(
        "Tools for investigating Wealthsimple customer issues. "
        "Provides access to customer accounts, transactions, login history, "
        "communications, policy documents, and historical case data."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
)
