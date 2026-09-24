"""Offline tests of the Agent Core guardrails (fake model, no API key or Postgres).

- tool output truncation (TOOL_OUTPUT_MAX_CHARS);
- step limit (AGENT_RECURSION_LIMIT) -> explicit degraded diagnosis;
- the final summary receives the actual tool results;
- a reused thread (same fingerprint) sends only the new alert to the LLM;
- LLM endpoint choice (LLM_API_BASE, never OPENAI_API_BASE for a Groq key);
- a provider 429/413 error (agent or summary call) surfaces as an explicit error, not as a success;
- the diagnostic system prompt lists the metrics and labels of this stack;
- the last LLM call before the step limit is told to answer without tools;
- each Prometheus result starts with its PromQL query, even after truncation.
"""
import itertools

import httpx
import openai
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from agents.diagnostic import build_diagnostic_agent
from conftest import ToolCallingFakeModel, tool_call
from guardrails import degraded_diagnosis_message, invoke_diagnosis, tools_called, truncate_tool_output
from llm_settings import GROQ_OPENAI_BASE_URL, resolve_llm_settings
from nodes.llm import LLMRateLimitError
from prompts import LAST_STEP_INSTRUCTION
from tools import mcp_client, mlops_tools
from test_diagnostic_graph import alert_state

LLM_INPUTS = []


class RecordingFakeModel(ToolCallingFakeModel):
    """Fake model that records the messages it receives."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        LLM_INPUTS.append(list(messages))
        return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


class RateLimitedFakeModel(ToolCallingFakeModel):
    """Fake model whose provider answers with an HTTP error (after answers_before_error answers)."""

    status: int = 429
    answers_before_error: int = 0

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.answers_before_error > 0:
            self.answers_before_error -= 1
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        response = httpx.Response(self.status, request=request)
        if self.status == 429:
            raise openai.RateLimitError("Error code: 429 - rate limit reached", response=response, body=None)
        raise openai.APIStatusError("Error code: 413 - Request too large", response=response, body=None)


@tool
def PrometheusQuery(query: str) -> str:
    """Fake Prometheus query tool."""
    return "cpu=95%"


@tool
def BigLogSearch(query: str) -> str:
    """Fake tool returning a very large output."""
    return "x" * 5000


@pytest.fixture(autouse=True)
def reset_inputs():
    LLM_INPUTS.clear()


def recording_model(*messages):
    return RecordingFakeModel(messages=iter(list(messages)))


def all_text(messages):
    return "\n".join(str(m.content) for m in messages)


def test_tool_output_is_truncated_before_reaching_the_llm(monkeypatch):
    monkeypatch.setenv("TOOL_OUTPUT_MAX_CHARS", "100")
    llm = recording_model(
        tool_call("BigLogSearch", {"query": "errors"}),
        AIMessage(content="done"),
        AIMessage(content="Diagnostic final"),
    )
    result = build_diagnostic_agent(llm, [BigLogSearch]).invoke(alert_state())
    tool_msg = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert tool_msg.content.startswith("x" * 100)
    assert "[truncated: 4900 of 5000 characters removed (TOOL_OUTPUT_MAX_CHARS=100)]" in tool_msg.content
    assert len(tool_msg.content) < 300


def test_truncate_keeps_short_outputs_unchanged():
    assert truncate_tool_output("short", max_chars=10) == "short"


def test_step_limit_forces_a_partial_diagnosis(monkeypatch):
    """Close to AGENT_RECURSION_LIMIT the next tool call is skipped and the summary is written."""
    monkeypatch.setenv("AGENT_RECURSION_LIMIT", "6")
    llm = recording_model(
        tool_call("PrometheusQuery", {"query": "up"}, "c1"),
        tool_call("PrometheusQuery", {"query": "rate(cpu[5m])"}, "c2"),  # skipped: step limit
        AIMessage(content="Résumé partiel : cpu=95%"),
    )
    agent = build_diagnostic_agent(llm, [PrometheusQuery], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "loop"}}

    state, reason = invoke_diagnosis(agent, alert_state(), config)

    assert reason == "recursion_limit"
    assert tools_called(state["messages"]) == ["PrometheusQuery"]
    assert state["final_result"] == "Résumé partiel : cpu=95%"
    message = degraded_diagnosis_message(state)
    assert message.startswith("Partial diagnosis: the agent reached the step limit (AGENT_RECURSION_LIMIT=6)")
    assert "Résumé partiel : cpu=95%" in message


def test_graph_recursion_error_gives_explicit_degraded_result(monkeypatch):
    monkeypatch.setenv("AGENT_RECURSION_LIMIT", "2")
    endless = ToolCallingFakeModel(
        messages=itertools.cycle([tool_call("PrometheusQuery", {"query": "up"})])
    )
    state, reason = invoke_diagnosis(build_diagnostic_agent(endless, [PrometheusQuery]), alert_state())

    assert reason == "recursion_limit"
    assert state["final_result"] is None
    assert "No final diagnosis was produced" in degraded_diagnosis_message(state)


def test_normal_run_is_not_degraded():
    llm = recording_model(AIMessage(content="ok"), AIMessage(content="Diagnostic final"))
    state, reason = invoke_diagnosis(build_diagnostic_agent(llm, [PrometheusQuery]), alert_state())
    assert reason is None
    assert state["final_result"] == "Diagnostic final"


def test_final_summary_receives_the_tool_results():
    llm = recording_model(
        tool_call("PrometheusQuery", {"query": "rate(cpu[5m])"}),
        AIMessage(content="CPU saturé"),
        AIMessage(content="Diagnostic final : CPU à 95 %"),
    )
    result = build_diagnostic_agent(llm, [PrometheusQuery]).invoke(alert_state())

    summary_prompt = all_text(LLM_INPUTS[-1])
    assert "Prometheus data: cpu=95%" in summary_prompt
    assert "Investigation notes: CPU saturé" in summary_prompt
    assert result["prometheus_data"] == "cpu=95%"
    assert tools_called(result["messages"]) == ["PrometheusQuery"]


def test_system_prompt_lists_the_available_metrics_and_labels():
    """The agent is told which PromQL/LogQL queries return data in this stack."""
    llm = recording_model(AIMessage(content="ok"), AIMessage(content="Diagnostic final"))
    build_diagnostic_agent(llm, [PrometheusQuery]).invoke(alert_state())

    system_prompt = str(LLM_INPUTS[0][0].content)
    # Braces of the PromQL/LogQL examples reach the model unchanged (no template formatting)
    assert 'rate(node_cpu_seconds_total{mode="idle"}[5m])' in system_prompt
    assert 'up{job="news_classifier_api"}' in system_prompt
    assert '{job="docker", service="news-classifier-api"}' in system_prompt
    assert "container_*" in system_prompt  # named as missing, so the model does not query it


def test_reused_thread_sends_only_the_new_alert_to_the_llm():
    llm = recording_model(
        AIMessage(content="r1"), AIMessage(content="final 1"),
        AIMessage(content="r2"), AIMessage(content="final 2"),
    )
    graph = build_diagnostic_agent(llm, [PrometheusQuery], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "alert_diagnosis_same-fingerprint"}}
    graph.invoke(alert_state("premiere alerte"), config)
    graph.invoke(alert_state("deuxieme alerte"), config)

    second_run_first_call = all_text(LLM_INPUTS[2])
    assert "deuxieme alerte" in second_run_first_call
    assert "premiere alerte" not in second_run_first_call
    # The checkpoint still holds both runs, each message once (no history duplication).
    messages = graph.get_state(config).values["messages"]
    assert [m.content for m in messages if isinstance(m, HumanMessage)] == ["premiere alerte", "deuxieme alerte"]
    assert len(messages) == 6


def test_groq_key_never_uses_openai_api_base(monkeypatch):
    for name in ("OPENAI_API_KEY", "OPENAI_MODEL_NAME", "LLM_API_BASE", "GROQ_MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("OPENAI_API_BASE", "https://api.openai.com/v1")  # set by docker-compose for embeddings

    assert resolve_llm_settings() == ("openai/gpt-oss-20b", "gsk-test", GROQ_OPENAI_BASE_URL)

    monkeypatch.setenv("LLM_API_BASE", "https://gateway.example/v1")
    monkeypatch.setenv("GROQ_MODEL_NAME", "custom-model")
    assert resolve_llm_settings() == ("custom-model", "gsk-test", "https://gateway.example/v1")


def test_openai_settings_keep_openai_api_base(monkeypatch):
    monkeypatch.delenv("LLM_API_BASE", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_BASE", "https://proxy.example/v1")
    assert resolve_llm_settings() == ("gpt-4o-mini", "sk-test", "https://proxy.example/v1")


@pytest.mark.parametrize("status", [429, 413])
def test_rate_limit_is_an_explicit_error_not_a_success(status):
    agent = build_diagnostic_agent(RateLimitedFakeModel(messages=iter([]), status=status), [PrometheusQuery])
    with pytest.raises(LLMRateLimitError) as excinfo:
        agent.invoke(alert_state())
    assert excinfo.value.provider_status == status
    assert "LLM rate limited" in str(excinfo.value)


def test_rate_limit_on_the_summary_call_is_an_explicit_error():
    """The agent answers, then the provider refuses the final summary call."""
    llm = RateLimitedFakeModel(messages=iter([AIMessage(content="CPU saturé")]), answers_before_error=1)
    with pytest.raises(LLMRateLimitError) as excinfo:
        build_diagnostic_agent(llm, [PrometheusQuery]).invoke(alert_state())
    assert excinfo.value.provider_status == 429


def test_last_step_asks_for_the_diagnosis_and_a_direct_answer_is_a_success(monkeypatch):
    """Limit 12: the 5th LLM call (remaining_steps=3) is told to answer without tools."""
    monkeypatch.setenv("AGENT_RECURSION_LIMIT", "12")
    llm = recording_model(
        *[tool_call("PrometheusQuery", {"query": f"q{i}"}, f"c{i}") for i in range(1, 5)],
        AIMessage(content="Diagnostic direct : cpu=95%"),
        AIMessage(content="Diagnostic final"),
    )
    state, reason = invoke_diagnosis(build_diagnostic_agent(llm, [PrometheusQuery]), alert_state())

    agent_calls = LLM_INPUTS[:5]
    assert all(LAST_STEP_INSTRUCTION not in all_text(call) for call in agent_calls[:4])
    assert agent_calls[4][-1].content == LAST_STEP_INSTRUCTION
    assert reason is None  # answered without a tool: "success", not "degraded"
    assert state["final_result"] == "Diagnostic final"
    assert tools_called(state["messages"]) == ["PrometheusQuery"] * 4
    # The note goes to the LLM only: it is not stored in the graph state.
    assert LAST_STEP_INSTRUCTION not in all_text(state["messages"])


class _Resp:
    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        pass


@pytest.mark.parametrize("transport", ["http", "mcp"])
def test_prometheus_result_starts_with_its_query_even_when_truncated(transport, monkeypatch):
    promql = 'up{job="news_classifier_api"}'
    service_result = "Prometheus query results:\n{  } values: " + ", ".join(["12.80"] * 500)
    monkeypatch.setenv("TOOL_OUTPUT_MAX_CHARS", "200")
    monkeypatch.setattr(mlops_tools, "PROMETHEUS_TRANSPORT", transport)
    monkeypatch.setattr(mlops_tools.requests, "post", lambda *a, **k: _Resp({"result": service_result}))
    monkeypatch.setattr(mcp_client, "call_tool", lambda *a, **k: service_result)
    llm = recording_model(
        tool_call("PrometheusQuery", {"query": promql}),
        AIMessage(content="ok"),
        AIMessage(content="Diagnostic final"),
    )
    result = build_diagnostic_agent(llm, [mlops_tools.PrometheusQuery]).invoke(alert_state())

    tool_msg = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    assert tool_msg.content.startswith(f"PromQL query: {promql}\nPrometheus query results:\n")
    assert "(TOOL_OUTPUT_MAX_CHARS=200)]" in tool_msg.content
    assert f"Prometheus data: PromQL query: {promql}\n" in all_text(LLM_INPUTS[-1])


def test_prometheus_error_also_names_its_query(monkeypatch):
    def failing_post(*args, **kwargs):
        raise ConnectionError("prometheus-tool unreachable")

    monkeypatch.setattr(mlops_tools, "PROMETHEUS_TRANSPORT", "http")
    monkeypatch.setattr(mlops_tools.requests, "post", failing_post)
    monkeypatch.setattr(mlops_tools.prom_breaker, "failures", 0)
    monkeypatch.setattr(mlops_tools.prom_breaker, "state", "CLOSED")
    result = mlops_tools.PrometheusQuery.invoke({"query": "node_load1"})
    assert result == "PromQL query: node_load1\nError: prometheus-tool unreachable"
