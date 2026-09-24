"""Chapter 6: the Agent Core calls the Prometheus tool through MCP (fake model).

- offline test: the MCP client is routed in memory to the real handle_mcp_request;
- `stack` test: same call against the running stack (make all), run with -m stack.
"""
import os
import sys

import pytest
from langchain_core.messages import AIMessage, ToolMessage

HERE = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(HERE, "../../src/tool_services/prometheus_tool")))

from mcp_server import PROTOCOL_VERSION, handle_mcp_request  # noqa: E402
from agents.diagnostic import build_diagnostic_agent  # noqa: E402
from tools import mcp_client, mlops_tools  # noqa: E402
from conftest import tool_call  # noqa: E402
from test_diagnostic_graph import alert_state  # noqa: E402

PROMQL = 'rate(process_cpu_seconds_total{job="news-classifier-api"}[5m])'


class _Resp:
    def __init__(self, body, status):
        self._body, self.status_code = body, status

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def agent_with_prometheus_call(fake_model):
    llm = fake_model(
        tool_call("PrometheusQuery", {"query": PROMQL, "time_range_minutes": 30}),
        AIMessage(content="CPU élevé confirmé"),
        AIMessage(content="Diagnostic final"),
    )
    return build_diagnostic_agent(llm, [mlops_tools.PrometheusQuery])


def test_agent_calls_prometheus_through_mcp(fake_model, monkeypatch):
    received = []

    def run_tool(name, arguments):
        received.append((name, arguments))
        return "Prometheus result: cpu=0.93"

    def fake_post(url, json, headers, timeout):
        assert url.endswith("/mcp")
        lower = {k.lower(): v for k, v in headers.items()}
        return _Resp(*handle_mcp_request(json, lower, run_tool))

    monkeypatch.setattr(mlops_tools, "PROMETHEUS_TRANSPORT", "mcp")
    monkeypatch.setattr(mcp_client.requests, "post", fake_post)

    result = agent_with_prometheus_call(fake_model).invoke(alert_state())

    assert received and received[0][0] == "prometheus.query_range"
    assert received[0][1]["query"] == PROMQL
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    # The Agent Core puts the query on the first line of the result (HTTP and MCP alike).
    assert tool_msgs[0].content == f"PromQL query: {PROMQL}\nPrometheus result: cpu=0.93"


def test_mcp_client_lists_catalog_in_memory(monkeypatch):
    monkeypatch.setattr(
        mcp_client.requests, "post",
        lambda url, json, headers, timeout: _Resp(*handle_mcp_request(
            json, {k.lower(): v for k, v in headers.items()}, lambda *_: "")),
    )
    assert [t["name"] for t in mcp_client.list_tools("http://in-memory")] == ["prometheus.query_range"]


STACK_URL = os.getenv("PROMETHEUS_TOOL_URL", "http://localhost:8001")


@pytest.mark.stack
def test_stack_tools_list_and_agent_tool_call(fake_model, monkeypatch):
    assert "prometheus.query_range" in [t["name"] for t in mcp_client.list_tools(STACK_URL)]

    monkeypatch.setattr(mlops_tools, "PROMETHEUS_TRANSPORT", "mcp")
    monkeypatch.setattr(mlops_tools, "PROMETHEUS_TOOL_SERVICE_URL", STACK_URL)
    result = agent_with_prometheus_call(fake_model).invoke(alert_state())

    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert tool_msgs and "Service Unavailable" not in tool_msgs[0].content
    print("\nMCP tool result:", tool_msgs[0].content[:300])
