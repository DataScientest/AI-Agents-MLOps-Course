"""Tests de l'agent Calculatrice (chapitre 1) avec un modèle factice."""
import os
import re

import pytest
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import Tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

import src.main as main_module
from tests.conftest import tool_call
from tools.calculator import Calculator, CalculatorInput

SYSTEM_PROMPT = "Tu es un Calculateur Expert."


def calculator_tools():
    return [
        Tool(
            name="Calculatrice",
            func=Calculator,
            description="Évalue une expression mathématique, ex: 'sqrt(144) + 5'.",
            args_schema=CalculatorInput,
        )
    ]


def test_compiled_graph_runs_react_loop(fake_model):
    """Graphe compilé exécuté : Raisonner -> Agir (outil) -> Observer -> Réponse."""
    llm = fake_model(
        tool_call("Calculatrice", {"expression": "sqrt(144) + 5"}),
        AIMessage(content="La réponse est 17.0"),
    )
    agent = create_agent(llm, calculator_tools(), system_prompt=SYSTEM_PROMPT)

    result = agent.invoke({"messages": [HumanMessage(content="Racine de 144 plus 5 ?")]})

    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert [m.content for m in tool_messages] == ["17.0"]
    assert result["messages"][-1].content == "La réponse est 17.0"


def test_conditional_branch_two_paths(fake_model):
    """Branche 1 : appel d'outil. Branche 2 : réponse directe, sans outil."""
    with_tool = create_agent(
        fake_model(tool_call("Calculatrice", {"expression": "2 + 2"}), AIMessage(content="4")),
        calculator_tools(),
    ).invoke({"messages": [HumanMessage(content="2 + 2 ?")]})
    without_tool = create_agent(
        fake_model(AIMessage(content="Oui, le ciel est bleu.")), calculator_tools()
    ).invoke({"messages": [HumanMessage(content="Le ciel est-il bleu ?")]})

    assert any(isinstance(m, ToolMessage) for m in with_tool["messages"])
    assert not any(isinstance(m, ToolMessage) for m in without_tool["messages"])


def test_loop_stops_when_model_stops_calling_tools(fake_model):
    """La boucle ReAct enchaîne plusieurs outils et s'arrête sans tool_calls."""
    llm = fake_model(
        tool_call("Calculatrice", {"expression": "123 * 456"}, "c1"),
        tool_call("Calculatrice", {"expression": "56088 + 789"}, "c2"),
        AIMessage(content="56877"),
    )
    result = create_agent(llm, calculator_tools()).invoke(
        {"messages": [HumanMessage(content="(123 * 456) + 789")]}
    )
    assert [m.content for m in result["messages"] if isinstance(m, ToolMessage)] == ["56088", "56877"]
    assert result["messages"][-1].content == "56877"


def test_recursion_limit_stops_runaway_loop(fake_model):
    """recursion_limit (cf. cours, partie 2) coupe une boucle infinie."""
    from langgraph.errors import GraphRecursionError

    llm = fake_model(*[tool_call("Calculatrice", {"expression": "1 + 1"}, f"c{i}") for i in range(50)])
    agent = create_agent(llm, calculator_tools())
    with pytest.raises(GraphRecursionError):
        agent.invoke({"messages": [HumanMessage(content="boucle")]}, config={"recursion_limit": 5})


def test_human_in_the_loop_interrupt_and_resume(fake_model):
    """interrupt() avant l'outil, reprise avec Command(resume=...)."""
    llm = fake_model(
        tool_call("Calculatrice", {"expression": "789 - 123"}),
        AIMessage(content="666"),
    )
    agent = create_agent(
        llm,
        calculator_tools(),
        middleware=[HumanInTheLoopMiddleware(interrupt_on={"Calculatrice": True})],
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "hitl"}}

    paused = agent.invoke({"messages": [HumanMessage(content="789 - 123 ?")]}, config)
    assert "__interrupt__" in paused
    assert not any(isinstance(m, ToolMessage) for m in paused["messages"])

    resumed = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config)
    assert [m.content for m in resumed["messages"] if isinstance(m, ToolMessage)] == ["666"]
    assert resumed["messages"][-1].content == "666"


def test_checkpointer_persists_between_two_calls(fake_model):
    """Deux invoke sur le même thread_id : l'historique est conservé."""
    llm = fake_model(AIMessage(content="Bonjour Alice"), AIMessage(content="Tu t'appelles Alice"))
    agent = create_agent(llm, calculator_tools(), checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "memoire"}}

    agent.invoke({"messages": [HumanMessage(content="Je m'appelle Alice")]}, config)
    second = agent.invoke({"messages": [HumanMessage(content="Comment je m'appelle ?")]}, config)

    humans = [m.content for m in second["messages"] if isinstance(m, HumanMessage)]
    assert humans == ["Je m'appelle Alice", "Comment je m'appelle ?"]
    other_thread = agent.get_state({"configurable": {"thread_id": "autre"}})
    assert not other_thread.values


def test_main_runs_end_to_end_with_fake_llm(fake_model, monkeypatch, capsys):
    """src/main.py tourne de bout en bout ; le modèle vient de GROQ_MODEL_NAME."""
    answers = [
        tool_call("Calculatrice", {"expression": "sqrt(144) + 5"}),
        AIMessage(content="17.0"),
    ] + [AIMessage(content=f"réponse {i}") for i in range(5)]
    captured = {}

    def fake_chat_openai(**kwargs):
        captured.update(kwargs)
        llm = fake_model(*answers)
        llm.__dict__["model_name"] = kwargs["model"]
        return llm

    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    monkeypatch.setenv("GROQ_MODEL_NAME", "mon-modele")
    monkeypatch.setattr(main_module, "load_dotenv", lambda **_: None, raising=False)
    monkeypatch.setattr(main_module, "ChatOpenAI", fake_chat_openai)
    monkeypatch.chdir(os.path.dirname(os.path.dirname(__file__)))

    main_module.main()

    out = capsys.readouterr().out
    assert captured["model"] == "mon-modele"
    assert "Réponse finale de l'agent: 17.0" in out
    assert "Fin des tests de l'agent" in out


@pytest.mark.live
def test_live_agent_uses_calculator():
    """Appel réel (GROQ_API_KEY requis) : pytest -m live."""
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=os.getenv("GROQ_MODEL_NAME", "openai/gpt-oss-20b"),
        temperature=0,
        api_key=os.environ["GROQ_API_KEY"],
        base_url=os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1"),
    )
    result = create_agent(llm, calculator_tools(), system_prompt=SYSTEM_PROMPT).invoke(
        {"messages": [HumanMessage(content="Calcule (123 * 456) + 789")]}
    )
    assert any(isinstance(m, ToolMessage) for m in result["messages"])
    digits = re.sub(r"\D", "", result["messages"][-1].content)  # "56 877" (U+202F), "56,877"...
    assert "56877" in digits
