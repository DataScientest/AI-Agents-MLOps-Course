"""
Test script for Chapter 4 - Part 2 & 3: RAG and Feedback functionality

This script tests:
1. Knowledge base connection
2. RAG search functionality
3. Feedback recording
4. Alert type confidence tracking

Run after docker-compose up and loading sample incidents.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "aiops_agent_monitor"))

print("=" * 70)
print("Chapter 4 - RAG and Feedback System Tests")
print("=" * 70)

# Test 1: Knowledge Base Connection
print("\n=== Test 1: Knowledge Base Connection ===")
try:
    from knowledge_base import get_kb_client
    kb_client = get_kb_client()
    print("✓ Knowledge base client initialized successfully")
    print(f"  Client type: {type(kb_client).__name__}")
except Exception as e:
    print(f"✗ Failed to initialize KB client: {e}")
    sys.exit(1)

# Test 2: RAG Search (requires incidents to be loaded)
print("\n=== Test 2: RAG Semantic Search ===")
try:
    from tools.mlops_tools import RAGKnowledgeSearch

    test_queries = [
        {
            "query": "High CPU usage during deployment",
            "service_name": "news-classifier-api",
            "top_k": 3
        },
        {
            "query": "Memory leak causing restarts",
            "service_name": "news-classifier-api",
            "top_k": 2
        },
        {
            "query": "Disk space issues with logs",
            "service_name": None,
            "top_k": 2
        }
    ]

    for i, test in enumerate(test_queries, 1):
        print(f"\n  Test 2.{i}: Query: '{test['query']}'")
        result = RAGKnowledgeSearch.invoke(test)
        print(f"  Result preview (first 200 chars):")
        print(f"  {result[:200]}...")
        if "Found" in result:
            print("  ✓ RAG search returned results")
        else:
            print("  ⚠ No results found (might need to load incidents)")

except Exception as e:
    print(f"✗ RAG search failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Feedback Recording
print("\n=== Test 3: Diagnosis Feedback Recording ===")
try:
    from knowledge_base import DiagnosisFeedback

    test_feedback = DiagnosisFeedback(
        diagnosis_id="test-diag-001",
        thread_id="test-thread-001",
        alert_info="Test alert: High CPU on news-classifier-api",
        service_name="news-classifier-api",
        alert_type="HighCPULoad",
        proposed_root_cause="Docker cache conflict",
        proposed_solution="Clear build cache",
        confidence_score=0.85,
        outcome="success",
        human_correction="Solution worked perfectly",
        diagnosed_at=datetime.now(),
        feedback_received_at=datetime.now(),
    )

    feedback_id = kb_client.record_diagnosis_feedback(test_feedback)
    print(f"✓ Feedback recorded successfully with id={feedback_id}")

except Exception as e:
    print(f"✗ Feedback recording failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Alert Type Confidence Retrieval
print("\n=== Test 4: Alert Type Confidence Scores ===")
try:
    stats = kb_client.get_alert_type_confidence(
        service_name="news-classifier-api",
        alert_type="HighCPULoad"
    )

    if stats:
        print(f"✓ Retrieved confidence stats for HighCPULoad:")
        print(f"  Total diagnoses: {stats.total_diagnoses}")
        print(f"  Successful: {stats.successful_diagnoses}")
        print(f"  Failed: {stats.failed_diagnoses}")
        print(f"  Confidence score: {stats.confidence_score:.2%}")
    else:
        print("  ⚠ No stats found yet (provide more feedback to generate stats)")

except Exception as e:
    print(f"✗ Stats retrieval failed: {e}")

# Test 5: Adding Incident to Knowledge Base
print("\n=== Test 5: Adding Incident to Knowledge Base ===")
try:
    from knowledge_base import Incident

    test_incident = Incident(
        incident_id="TEST-INC-001",
        service_name="news-classifier-api",
        alert_type="TestAlert",
        severity="medium",
        summary="Test incident for verification",
        root_cause="Test root cause",
        solution="Test solution",
        occurred_at=datetime.now(),
        resolved_at=datetime.now(),
        resolution_time_seconds=300,
    )

    incident_id = kb_client.add_incident(test_incident)
    print(f"✓ Test incident added successfully with id={incident_id}")
    print(f"  Note: Embedding was generated automatically")

    # Verify it can be retrieved
    similar = kb_client.search_similar_incidents(
        query="Test incident verification",
        service_name="news-classifier-api",
        top_k=1
    )

    if similar and similar[0].incident.incident_id == "TEST-INC-001":
        print(f"✓ Test incident can be retrieved via semantic search")
        print(f"  Similarity score: {similar[0].similarity_score:.3f}")
    else:
        print("  ⚠ Could not retrieve test incident")

except Exception as e:
    print(f"✗ Incident addition failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✓ Chapter 4 RAG and Feedback Tests Completed")
print("=" * 70)
print("\nNext steps:")
print("1. If incidents not loaded, run: uv run scripts/load_sample_incidents.py")
print("2. Test with agent: Send diagnosis request to http://localhost:8005/diagnose_alert")
print("3. Submit feedback via: POST http://localhost:8005/feedback")
