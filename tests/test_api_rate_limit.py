"""Offline test of the Agent Core API: a provider 429/413 becomes an explicit HTTP 429.

Needs the service dependencies (fastapi, prometheus_client), which are not in the
course environment. Run it with:
uv run --with fastapi==0.116.1 --with prometheus_client==0.22.1 pytest tests/test_api_rate_limit.py
"""
import pytest
from langchain_core.messages import AIMessage

pytest.importorskip("fastapi")
pytest.importorskip("prometheus_client")

from fastapi.testclient import TestClient  # noqa: E402

from agents.diagnostic import build_diagnostic_agent  # noqa: E402
from tests.test_guardrails import PrometheusQuery, RateLimitedFakeModel  # noqa: E402

ALERT = {"alerts": [{"labels": {"alertname": "HighCPULoad", "service": "news-classifier-api"},
                     "annotations": {"summary": "CPU above 90%"}}]}


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")  # main.py builds its LLM client at import
    import main
    return main


@pytest.mark.parametrize("answers_before_error", [0, 1], ids=["agent_call", "summary_call"])
def test_rate_limited_provider_gives_http_429(api, monkeypatch, answers_before_error):
    llm = RateLimitedFakeModel(messages=iter([AIMessage(content="CPU saturé")]),
                               answers_before_error=answers_before_error)
    monkeypatch.setattr(api, "DIAGNOSTIC_AGENT", build_diagnostic_agent(llm, [PrometheusQuery]))

    response = TestClient(api.app).post("/diagnose_alert", json=ALERT)

    assert response.status_code == 429
    assert response.json()["detail"].startswith("LLM rate limited (provider HTTP 429)")
