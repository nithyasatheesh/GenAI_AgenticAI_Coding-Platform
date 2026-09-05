"""Bundled MCP server (stdio transport) used by the MCP practical lab.

The MCP lab spawns THIS file as a real subprocess and talks to it over the
Model Context Protocol (JSON-RPC on stdio) via `langchain-mcp-adapters`.

Run it standalone to sanity-check:  python mcp_server.py   (it will wait on stdio)
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sandbox-tools")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def leave_allowance(kind: str) -> str:
    """Annual leave-day allowance for a leave type: 'casual', 'sick', or 'earned'."""
    table = {"casual": "12 days", "sick": "10 days", "earned": "18 days"}
    return table.get(kind.strip().lower(), f"unknown leave type: {kind!r}")


@mcp.resource("policy://notice-period")
def notice_period() -> str:
    """The standard notice period for regular full-time employees."""
    return "60 calendar days"


if __name__ == "__main__":
    mcp.run(transport="stdio")
