"""Minimal MCP 2026-07-28 (v2) client.

One stateless POST per call — no handshake, no session. This is deliberately
the same shape as the HTTP proxy pattern from Chapter 5: the caller keeps
owning timeout, circuit breaker, and error handling.
"""
import requests

PROTOCOL_VERSION = "2026-07-28"

CLIENT_META = {
    "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
    "io.modelcontextprotocol/clientInfo": {"name": "aiops-agent-core", "version": "1.0.0"},
    "io.modelcontextprotocol/clientCapabilities": {},
}


def _headers(method: str, name: str | None = None) -> dict:
    headers = {
        "MCP-Protocol-Version": PROTOCOL_VERSION,
        "Mcp-Method": method,
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if name is not None:
        headers["Mcp-Name"] = name
    return headers


def list_tools(base_url: str, timeout: int = 30) -> list:
    """Fetch the server's tool catalog (cacheable per ttlMs/cacheScope)."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": CLIENT_META}}
    resp = requests.post(f"{base_url}/mcp", json=body, headers=_headers("tools/list"), timeout=timeout)
    resp.raise_for_status()
    return resp.json()["result"]["tools"]


def call_tool(base_url: str, name: str, arguments: dict, timeout: int = 30) -> str:
    """Call one MCP tool and return its text content.

    Raises on transport/protocol errors so a surrounding circuit breaker
    counts them as failures; tool-level errors (isError) are returned as text
    for the LLM to read, mirroring the legacy proxy behavior.
    """
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments, "_meta": CLIENT_META},
    }
    resp = requests.post(f"{base_url}/mcp", json=body, headers=_headers("tools/call", name), timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    if "error" in payload:
        raise RuntimeError(f"MCP error {payload['error']['code']}: {payload['error']['message']}")
    result = payload["result"]
    return "".join(c["text"] for c in result["content"] if c["type"] == "text")
