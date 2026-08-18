import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/tool_services/prometheus_tool")))

from mcp_server import handle_mcp_request, PROTOCOL_VERSION, HEADER_MISMATCH, METHOD_NOT_FOUND


def _headers(method, name=None):
    h = {"mcp-protocol-version": PROTOCOL_VERSION, "mcp-method": method}
    if name:
        h["mcp-name"] = name
    return h


def _meta():
    return {
        "io.modelcontextprotocol/protocolVersion": PROTOCOL_VERSION,
        "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "0"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }


def fake_tool(name, arguments):
    return f"result for {arguments['query']}"


def test_tools_list_returns_catalog_with_cache_metadata():
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": _meta()}}
    response, status = handle_mcp_request(body, _headers("tools/list"), fake_tool)
    assert status == 200
    result = response["result"]
    assert result["resultType"] == "complete"
    assert result["tools"][0]["name"] == "prometheus.query_range"
    assert result["ttlMs"] > 0
    assert result["cacheScope"] == "public"


def test_tools_call_returns_text_content():
    body = {
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "prometheus.query_range", "arguments": {"query": "up"}, "_meta": _meta()},
    }
    response, status = handle_mcp_request(body, _headers("tools/call", "prometheus.query_range"), fake_tool)
    assert status == 200
    result = response["result"]
    assert result["isError"] is False
    assert result["content"] == [{"type": "text", "text": "result for up"}]


def test_tool_error_is_reported_in_band():
    body = {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "prometheus.query_range", "arguments": {"query": "up"}, "_meta": _meta()},
    }
    response, status = handle_mcp_request(
        body, _headers("tools/call", "prometheus.query_range"), lambda n, a: "Error: boom"
    )
    assert status == 200
    assert response["result"]["isError"] is True


def test_missing_protocol_version_is_rejected():
    body = {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}}
    response, status = handle_mcp_request(body, {"mcp-method": "tools/list"}, fake_tool)
    assert status == 400
    assert response["error"]["code"] == HEADER_MISMATCH


def test_name_header_mismatch_is_rejected():
    body = {
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "prometheus.query_range", "arguments": {}, "_meta": _meta()},
    }
    response, status = handle_mcp_request(body, _headers("tools/call", "wrong.name"), fake_tool)
    assert status == 400
    assert response["error"]["code"] == HEADER_MISMATCH


def test_unknown_method_returns_404():
    body = {"jsonrpc": "2.0", "id": 6, "method": "resources/list", "params": {}}
    response, status = handle_mcp_request(body, _headers("resources/list"), fake_tool)
    assert status == 404
    assert response["error"]["code"] == METHOD_NOT_FOUND
