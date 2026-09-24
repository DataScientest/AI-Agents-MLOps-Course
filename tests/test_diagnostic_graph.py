"""Tests of the diagnostic graph (Agent Core) with a fake model, no API key."""
import os

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from agents.diagnostic import build_diagnostic_agent
from state import AgentState
from tests.conftest import tool_call

CALLS = []


@tool
def PrometheusQuery(query: str) -> str:
    """Fake Prometheus query tool."""
    CALLS.append(query)
    return "cpu=95%"


def alert_state(text="High CPU on news-classifier-api"):
    return {
        "messages": [HumanMessage(content=text)], "alert_info": text, "alert_severity": "critical",
        "prometheus_data": "", "loki_logs": "", "grafana_link": "", "final_result": None,
    }


@pytest.fixture(autouse=True)
def reset_calls():
    CALLS.clear()


def test_graph_compiles_and_runs_with_tool(fake_model):
    llm = fake_model(
        tool_call("PrometheusQuery", {"query": "rate(cpu[5m])"}),
        AIMessage(content="CPU saturé"),
        AIMessage(content="Diagnostic final : CPU saturé"),
    )
    result = build_diagnostic_agent(llm, [PrometheusQuery]).invoke(alert_state())
    assert CALLS == ["rate(cpu[5m])"]
    assert any(isinstance(m, ToolMessage) and m.content == "cpu=95%" for m in result["messages"])
    assert result["final_result"] or result["messages"][-1].content


def test_conditional_branch_direct_answer_skips_tools(fake_model):
    llm = fake_model(AIMessage(content="Pas besoin d'outil"), AIMessage(content="Diagnostic final"))
    result = build_diagnostic_agent(llm, [PrometheusQuery]).invoke(alert_state())
    assert CALLS == []
    assert not any(isinstance(m, ToolMessage) for m in result["messages"])


def test_tool_loop_stops_when_llm_stops_calling_tools(fake_model):
    llm = fake_model(
        tool_call("PrometheusQuery", {"query": "q1"}, "c1"),
        tool_call("PrometheusQuery", {"query": "q2"}, "c2"),
        AIMessage(content="assez de données"),
        AIMessage(content="Diagnostic final"),
    )
    build_diagnostic_agent(llm, [PrometheusQuery]).invoke(alert_state())
    assert CALLS == ["q1", "q2"]


def test_checkpointer_persists_between_two_calls(fake_model):
    llm = fake_model(*[AIMessage(content=f"r{i}") for i in range(4)])
    graph = build_diagnostic_agent(llm, [PrometheusQuery]).builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "alert-1"}}
    graph.invoke(alert_state("premiere alerte"), config)
    graph.invoke({"messages": [HumanMessage(content="deuxieme alerte")]}, config)
    contents = [m.content for m in graph.get_state(config).values["messages"]]
    assert "premiere alerte" in contents and "deuxieme alerte" in contents


def test_interrupt_resumed_with_command():
    """Human approval before action: interrupt() then Command(resume=...)."""
    def approve(state: AgentState):
        decision = interrupt({"alert": state["alert_info"]})
        return {"final_result": decision}

    graph = StateGraph(AgentState)
    graph.add_node("approve", approve)
    graph.add_edge(START, "approve")
    graph.add_edge("approve", END)
    app = graph.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "hitl"}}

    paused = app.invoke(alert_state(), config)
    assert paused["__interrupt__"][0].value == {"alert": "High CPU on news-classifier-api"}
    assert app.invoke(Command(resume="approved"), config)["final_result"] == "approved"


@pytest.mark.live
def test_live_groq_model_answers():
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b"),
        api_key=os.environ["GROQ_API_KEY"],
        base_url=os.getenv("LLM_API_BASE") or "https://api.groq.com/openai/v1",
    )
    assert llm.invoke("Reply with the single word: pong").content
