"""Minimal MCP 2026-07-28 (v2) stateless server endpoint.

Implements the subset of the spec needed to expose this service's tool
over MCP: `tools/list` and `tools/call` as JSON-RPC 2.0 over a single
stateless POST. No sessions, no handshake — each request is self-describing,
which is exactly what makes it work behind an ordinary load balancer.

Spec references (2026-07-28):
- basic/transports/streamable-http: headers, error codes
- server/tools: tools/list and tools/call result shapes
"""
import logging
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2026-07-28"

# JSON-RPC error codes from the spec
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
HEADER_MISMATCH = -32020

# Tool catalog: name is prefixed ("prometheus.") to avoid collisions when a
# gateway aggregates several MCP servers (recommended by the Tools spec).
TOOLS = [
    {
        "name": "prometheus.query_range",
        "title": "Prometheus Range Query",
        "description": (
            "Executes a PromQL range query against Prometheus and returns "
            "formatted time-series results."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "PromQL query"},
                "time_range_minutes": {"type": "integer", "default": 5},
                "step_seconds": {"type": "integer", "default": 30},
                "target_service": {"type": ["string", "null"], "default": None},
            },
            "required": ["query"],
        },
    }
]

# The list is deterministic and stable, so we allow clients to cache it.
# ttlMs/cacheScope live directly in the result object (2026-07-28 spec).
TOOLS_LIST_TTL_MS = 300_000  # 5 minutes
TOOLS_LIST_CACHE_SCOPE = "public"


def _jsonrpc_error(request_id: Any, code: int, message: str) -> Dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_mcp_request(body: Dict, headers: Dict[str, str], call_tool: Callable[[str, Dict], str]) -> tuple[Dict, int]:
    """Handle one stateless MCP JSON-RPC request.

    Returns (response_body, http_status). `call_tool(name, arguments)` runs the
    actual tool implementation and returns its text result.
    """
    request_id = body.get("id")
    method = body.get("method")

    # --- Header validation (transport spec) ---
    proto = headers.get("mcp-protocol-version")
    if proto != PROTOCOL_VERSION:
        return (
            _jsonrpc_error(request_id, HEADER_MISMATCH,
                           f"Unsupported or missing MCP-Protocol-Version. Supported: {PROTOCOL_VERSION}"),
            400,
        )
    if headers.get("mcp-method") != method:
        return (
            _jsonrpc_error(request_id, HEADER_MISMATCH,
                           "Mcp-Method header must match the JSON-RPC method field."),
            400,
        )

    # --- tools/list ---
    if method == "tools/list":
        return (
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "resultType": "complete",
                    "tools": TOOLS,
                    "ttlMs": TOOLS_LIST_TTL_MS,
                    "cacheScope": TOOLS_LIST_CACHE_SCOPE,
                },
            },
            200,
        )

    # --- tools/call ---
    if method == "tools/call":
        params = body.get("params", {})
        name = params.get("name")
        if headers.get("mcp-name") != name:
            return (
                _jsonrpc_error(request_id, HEADER_MISMATCH,
                               "Mcp-Name header must match params.name."),
                400,
            )
        if name not in {t["name"] for t in TOOLS}:
            return (_jsonrpc_error(request_id, INVALID_PARAMS, f"Unknown tool: {name}"), 200)

        arguments = params.get("arguments", {})
        logger.info(f"MCP tools/call {name} args={arguments}")
        text = call_tool(name, arguments)
        # Tool-level failures are reported in-band via isError, not as
        # JSON-RPC errors (Tools spec): the LLM should see the error text.
        is_error = text.startswith("Error:")
        return (
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "resultType": "complete",
                    "content": [{"type": "text", "text": text}],
                    "isError": is_error,
                },
            },
            200,
        )

    # --- Unknown method (transport spec: 404 + -32601) ---
    return (_jsonrpc_error(request_id, METHOD_NOT_FOUND, f"Method not found: {method}"), 404)
