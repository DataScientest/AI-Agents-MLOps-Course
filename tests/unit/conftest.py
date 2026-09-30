"""Unit tests of the tool services.

Each service has its own `tool.py` (prometheus_tool/tool.py, loki_tool/tool.py, ...),
and each test file adds its service directory to sys.path before `from tool import ...`.
Without care, the first `tool` module imported stays in sys.modules and the next test
file gets the wrong one (ImportError: cannot import name 'LokiLogSearchTool' from 'tool').

Before each test file is imported, this hook forgets the previous service modules and
removes the service directories from sys.path, so every file imports its own `tool.py`.
"""
import os
import sys

import pytest

TOOL_SERVICES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "src", "tool_services")
)
# Module names shared by several services (tool.py) or loaded from a service directory.
SERVICE_MODULES = ("tool", "mcp_server", "main")


def _forget_service_modules() -> None:
    for name in SERVICE_MODULES:
        module = sys.modules.get(name)
        module_file = getattr(module, "__file__", None) or ""
        if module is not None and os.path.abspath(module_file).startswith(TOOL_SERVICES_DIR):
            del sys.modules[name]
    sys.path[:] = [p for p in sys.path if not os.path.abspath(p).startswith(TOOL_SERVICES_DIR)]


def pytest_collectstart(collector):
    if isinstance(collector, pytest.Module):
        _forget_service_modules()
