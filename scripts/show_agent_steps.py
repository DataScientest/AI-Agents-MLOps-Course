#!/usr/bin/env python3
"""Utility to extract key diagnostic steps from AIOps agent logs."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from typing import Iterable, List, Dict, Any, Optional


LOG_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (\w+) - (.*)$")

STEP_PATTERNS = [
    (
        re.compile(r"Received alert .*'(?P<alert>[^']+)' for service '(?P<service>[^']+)': (?P<detail>.*)"),
        lambda msg, m: {
            "action": "alert_received",
            "summary": f"Alert '{m.group('alert')}' received for service '{m.group('service')}'.",
            "detail": m.group('detail'),
        },
    ),
    (
        re.compile(r"Node 'llm_agent_node': (?P<detail>.*)"),
        lambda msg, m: {
            "action": "agent_node",
            "summary": "Agent is processing the alert and deciding next steps.",
            "detail": m.group('detail'),
        },
    ),
    (
        re.compile(r"Agent decided to use a tool\. (?P<detail>.*)"),
        lambda msg, m: {
            "action": "decision_tool",
            "summary": "Agent chose to invoke a diagnostic tool.",
            "detail": m.group('detail'),
        },
    ),
    (
        re.compile(r"Tool '(?P<tool>[^']+)' called with query: '(?P<query>[^']+)'.*service: (?P<service>[^\s]+)"),
        lambda msg, m: {
            "action": "tool_call",
            "summary": f"Invoked tool '{m.group('tool')}' targeting service '{m.group('service')}'.",
            "detail": f"Query: {m.group('query')}",
        },
    ),
    (
        re.compile(r"Function '(?P<tool>[^']+)' called with query: '(?P<query>[^']+)'.*service: (?P<service>[^\s]+)"),
        lambda msg, m: {
            "action": "tool_call",
            "summary": f"Invoked tool '{m.group('tool')}' targeting service '{m.group('service')}'.",
            "detail": f"Query: {m.group('query')}",
        },
    ),
    (
        re.compile(r"Prometheus query (?P<outcome>successful.*)"),
        lambda msg, m: {
            "action": "prometheus_result",
            "summary": "Prometheus query returned a result.",
            "detail": m.group('outcome'),
        },
    ),
    (
        re.compile(r"Loki query (?P<outcome>successful.*)"),
        lambda msg, m: {
            "action": "loki_result",
            "summary": "Loki log search completed.",
            "detail": m.group('outcome'),
        },
    ),
    (
        re.compile(r"Agent generated a direct response.*"),
        lambda msg, m: {
            "action": "agent_response",
            "summary": "Agent finished gathering data and is finalizing the diagnosis.",
            "detail": m.group(0),
        },
    ),
    (
        re.compile(r"Node 'finalize_diagnosis': (?P<detail>.*)"),
        lambda msg, m: {
            "action": "finalize",
            "summary": "Finalizing diagnosis narrative.",
            "detail": m.group('detail'),
        },
    ),
    (
        re.compile(r"Agent diagnostic run completed\. Final status: (?P<detail>.*)"),
        lambda msg, m: {
            "action": "diagnosis_complete",
            "summary": "Diagnostic run completed.",
            "detail": m.group('detail'),
        },
    ),
]


def _events_from_lines(lines: Iterable[str]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        match = LOG_PATTERN.match(line)
        if match:
            timestamp, level, message = match.groups()
            events.append({
                "timestamp": timestamp,
                "level": level,
                "message": message,
            })
        else:
            columns = line.split(" - ", maxsplit=2)
            if len(columns) == 3:
                timestamp, level, message = columns
                events.append({
                    "timestamp": timestamp.strip(),
                    "level": level.strip(),
                    "message": message.strip(),
                })

    return events


def _latest_session(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for idx in range(len(events) - 1, -1, -1):
        if "Received alert" in events[idx]["message"]:
            return events[idx:]
    return events


def parse_logs(lines: Iterable[str]) -> List[Dict[str, Any]]:
    events = _events_from_lines(lines)
    session_events = _latest_session(events)

    steps: List[Dict[str, Any]] = []

    for event in session_events:
        message = event["message"]
        for pattern, builder in STEP_PATTERNS:
            match = pattern.search(message)
            if match:
                step = {
                    "timestamp": event["timestamp"],
                    "level": event["level"],
                    "raw_message": message,
                }
                step.update(builder(message, match))
                steps.append(step)
                break

    if not steps:
        summary = "No diagnostic activity detected in the selected log window. Trigger an alert to generate a walkthrough."
        if session_events:
            summary += " Last log entry: " + session_events[-1]["message"]
        steps.append({
            "timestamp": session_events[-1]["timestamp"] if session_events else None,
            "level": session_events[-1]["level"] if session_events else "INFO",
            "action": "no_diagnostics",
            "summary": summary,
            "detail": None,
            "raw_message": session_events[-1]["message"] if session_events else None,
        })

    return steps


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "container name must be provided"}))
        sys.exit(1)

    container_name = sys.argv[1]
    steps = parse_logs(sys.stdin)

    output = {
        "container": container_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "step_count": len(steps),
        "steps": steps,
    }

    json.dump(output, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
