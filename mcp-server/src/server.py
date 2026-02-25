"""
MCP server entrypoint.

Imports all tool modules to trigger @mcp.tool() registration,
then starts the SSE server on mcp_host:mcp_port.
"""

from src.app import mcp

# Side-effect imports — registers @mcp.tool() decorators
from src.tools import accounts, knowledge, transactions  # noqa: F401

if __name__ == "__main__":
    mcp.run(transport="sse")
