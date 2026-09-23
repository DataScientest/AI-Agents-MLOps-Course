"""Tests of the 4 LangGraph patterns of chapter 2, with a fake model."""
import os

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import Tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from src.agents.agent_nodes import create_llm_tool_agent_node
from src.agents.conditional_agent import create_alert_router_agent
from src.agents.human_in_loop_agent import create_human_in_loop_agent
from src.agents.linear_agent import create_linear_report_agent
from src.agents.loop_agent import create_log_investigator_agent
from src.state import AgentState
from tests.conftest import tool_call


def full_state(**overrides):
    state = dict(
        messages=[], alert_info="", alert_severity="unknown", investigation_query="",
        investigation_step=0, max_investigation_steps=0, logs_found=False, proposed_action="",
        human_approval_needed=False, human_feedback="", system_metrics={}, report_content="",
        final_result=None,
    )
    state.update(overrides)
    return state


def test_linear_graph_compiles_and_runs(fake_model):
    agent = create_linear_report_agent(fake_model(AIMessage(content="Rapport CPU OK")), [])
    result = agent.invoke(full_state(messages=[HumanMessage(content="Generate a CPU health report.")]))
    assert result["messages"][-1].content


@pytest.mark.parametrize(
    "alert, expected",
    [("Critical service outage on production server!", "critical"),
     ("High CPU usage on ML analysis service.", "medium")],
)
def test_conditional_branching_two_paths(alert, expected):
    agent = create_alert_router_agent(None, [])
    result = agent.invoke(full_state(messages=[HumanMessage(content=alert)], alert_info=alert))
    assert result["alert_severity"] == expected


def test_loop_stops_on_max_steps(fake_model):
    agent = create_log_investigator_agent(fake_model(*[AIMessage(content="other_query")] * 5), [])
    result = agent.invoke(full_state(
        messages=[HumanMessage(content="Find logs")],
        investigation_query="non_existent_log_pattern", max_investigation_steps=2,
    ))
    assert result["logs_found"] is False
    assert result["investigation_step"] == 2


def test_loop_exits_when_logs_found(fake_model, monkeypatch):
    """End-to-end success exit: the tool finds logs, the loop stops without any LLM call."""
    monkeypatch.setattr("src.tools.mlops_tools.random.random", lambda: 0.0)  # search_logs always finds logs
    agent = create_log_investigator_agent(fake_model(), [])  # no message: any LLM call would fail
    result = agent.invoke(full_state(
        messages=[HumanMessage(content="Find logs concerning 'error'.")],
        investigation_query="error", max_investigation_steps=5,
    ))
    assert result["logs_found"] is True
    assert result["investigation_step"] == 1
    assert result["final_result"] == "Investigation completed: Relevant logs found."


def test_loop_refines_query_then_finds_logs(fake_model, monkeypatch):
    """First search finds nothing, the LLM suggests a query, the second search finds logs."""
    draws = iter([0.9, 0.0])  # 1st draw: nothing found; 2nd draw: logs found
    monkeypatch.setattr("src.tools.mlops_tools.random.random", lambda: next(draws))
    agent = create_log_investigator_agent(fake_model(AIMessage(content="error 500")), [])
    result = agent.invoke(full_state(
        messages=[HumanMessage(content="Find logs concerning 'error'.")],
        investigation_query="error", max_investigation_steps=5,
    ))
    assert result["logs_found"] is True
    assert result["investigation_step"] == 2
    assert result["investigation_query"] == "error 500"
    contents = [m.content for m in result["messages"]]
    assert len(contents) == len(set(contents))  # no duplicated history


@pytest.mark.parametrize(
    "logs_found, step, expected",
    [(True, 1, "end_investigation"), (False, 5, "end_investigation"), (False, 1, "search_logs_node")],
)
def test_loop_exit_conditions(logs_found, step, expected):
    from src.nodes.loop_agent import continue_investigation

    state = full_state(logs_found=logs_found, investigation_step=step, max_investigation_steps=5)
    assert continue_investigation(state) == expected


@pytest.mark.parametrize("feedback, node_message", [("approved", "Action applied"), ("rejected", "Action rejected")])
def test_human_in_loop_state_flag_pattern(fake_model, feedback, node_message, monkeypatch):
    """Pattern taught in chapter 2: pause on empty human_feedback, resume by re-invoking with the updated state."""
    # A single fake message: if the resume called propose_action (hence the LLM) again, the test would fail.
    agent = create_human_in_loop_agent(fake_model(AIMessage(content="Restart service X")), [])
    applied = []
    monkeypatch.setattr(
        "src.nodes.human_in_loop_agent.apply_action.apply_fix",
        lambda fix: applied.append(fix) or "Fix applied: Service restart requested.",
    )

    paused = agent.invoke(full_state(messages=[HumanMessage(content="Problem: high latency")]))
    assert paused["proposed_action"] == "Restart service X"
    assert paused.get("final_result") is None

    resumed = agent.invoke({**paused, "human_feedback": feedback})
    assert resumed["final_result"].startswith(node_message)
    assert resumed["proposed_action"] == "Restart service X"
    # The applied action is exactly the proposed one (and only when approved)
    assert applied == (["Restart service X"] if feedback == "approved" else [])
    proposals = [m for m in resumed["messages"] if m.content.startswith("Proposed action:")]
    assert len(proposals) == 1  # nodes only return their new messages


def test_interrupt_resumed_with_command_and_checkpointer():
    """LangGraph 1.x primitive: interrupt() + Command(resume=...) on the chapter state."""
    def propose(state: AgentState):
        return {"proposed_action": "Restart service X"}

    def ask_human(state: AgentState):
        decision = interrupt({"proposed_action": state["proposed_action"]})
        return {"human_feedback": decision}

    graph = StateGraph(AgentState)
    graph.add_node("propose", propose)
    graph.add_node("ask_human", ask_human)
    graph.add_edge(START, "propose")
    graph.add_edge("propose", "ask_human")
    graph.add_edge("ask_human", END)
    app = graph.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "hitl-1"}}

    paused = app.invoke(full_state(), config)
    assert paused["__interrupt__"][0].value == {"proposed_action": "Restart service X"}

    resumed = app.invoke(Command(resume="approved"), config)
    assert resumed["human_feedback"] == "approved"


def test_checkpointer_persists_between_two_calls(fake_model):
    agent = create_linear_report_agent(fake_model(AIMessage(content="r1"), AIMessage(content="r2")), [])
    graph = agent.builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t1"}}
    graph.invoke(full_state(messages=[HumanMessage(content="first")]), config)
    snapshot = graph.get_state(config)
    assert snapshot.values["messages"][0].content == "first"
    graph.invoke({"messages": [HumanMessage(content="second")]}, config)
    contents = [m.content for m in graph.get_state(config).values["messages"]]
    assert "first" in contents and "second" in contents


def test_llm_tool_agent_node_uses_create_agent(fake_model):
    add = Tool(name="Add", func=lambda e: str(eval(e)), description="Adds numbers")
    node = create_llm_tool_agent_node(
        fake_model(tool_call("Add", {"__arg1": "2+3"}), AIMessage(content="5")), [add]
    )
    out = node(full_state(messages=[HumanMessage(content="2+3?")]))
    assert out["messages"][-1].content == "5"


def test_setup_llm_reads_model_from_env(monkeypatch):
    import src.main as main_module

    monkeypatch.setattr(main_module, "load_dotenv", lambda **_: None)
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    monkeypatch.setenv("GROQ_MODEL_NAME", "mon-modele")
    assert main_module.setup_llm().model_name == "mon-modele"
    monkeypatch.delenv("GROQ_MODEL_NAME")
    assert main_module.setup_llm().model_name == "openai/gpt-oss-20b"


@pytest.mark.live
def test_live_linear_pattern_calls_llm():
    import src.main as main_module

    agent = create_linear_report_agent(main_module.setup_llm(), [])
    result = agent.invoke(full_state(messages=[HumanMessage(content="Generate a CPU health report.")]))
    assert result["messages"][-1].content.strip()
