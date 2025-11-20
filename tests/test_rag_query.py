#!/usr/bin/env python3
"""Test script for RAG knowledge base queries.

This script demonstrates how to query the knowledge base directly,
outside of the agent workflow. Use it to understand semantic search
and test different queries.

Usage:
    docker exec ai-agents-mlops-course-aiops-agent-monitor-1 python tests/test_rag_query.py
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/app')

from knowledge_base import get_kb_client


def main(query = "Memory usage growing over time, eventually hitting limits", 
        service = "news-classifier-api", 
        top_k = 3, 
        similarity_threshold = 0.6):

    """Query the knowledge base for similar incidents."""
    
    # Customize your query here
    #query = "Memory usage growing over time, eventually hitting limits"
    #service = "news-classifier-api"
    #top_k = 3
    #similarity_threshold = 0.6
    
    print("=" * 70)
    print("RAG Knowledge Base Query Test")
    print("=" * 70)
    print(f"\nQuery: '{query}'")
    print(f"Service filter: {service}")
    print(f"Top K: {top_k}")
    print(f"Similarity threshold: {similarity_threshold}")
    print("\n" + "=" * 70 + "\n")
    
    try:
        kb_client = get_kb_client()
        
        similar_incidents = kb_client.search_similar_incidents(
            query=query,
            service_name=service,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
        
        if not similar_incidents:
            print("❌ No similar incidents found.")
            print("\nTips:")
            print("  - Lower the similarity_threshold (try 0.5 or 0.4)")
            print("  - Check if incidents exist: docker exec -it postgres psql -U agent_user -d agent_checkpoints -c 'SELECT COUNT(*) FROM incident_knowledge;'")
            print("  - Try a different query or remove the service filter")
            return
        
        print(f"✅ Found {len(similar_incidents)} similar incident(s):\n")
        
        for i, similar in enumerate(similar_incidents, 1):
            incident = similar.incident
            print(f"{'─' * 70}")
            print(f"Incident {i} | Similarity: {similar.similarity_score:.2%}")
            print(f"{'─' * 70}")
            print(f"ID:          {incident.incident_id}")
            print(f"Alert Type:  {incident.alert_type}")
            print(f"Severity:    {incident.severity}")
            print(f"Summary:     {incident.summary}")
            print(f"Root Cause:  {incident.root_cause}")
            print(f"Solution:    {incident.solution}")
            print(f"Occurred:    {incident.occurred_at}")
            
            # Show confidence if available
            if incident.times_referenced > 0:
                success_rate = (incident.success_count / incident.times_referenced) * 100
                print(f"Track Record: {incident.success_count}/{incident.times_referenced} successful ({success_rate:.0f}%)")
            
            print()
        
        print("=" * 70)
        print("\n💡 Try modifying the query, service filter, or similarity threshold")
        print("   at the top of this script to see different results!\n")
        
    except Exception as e:
        print(f"❌ Error querying knowledge base: {e}")
        print("\nTroubleshooting:")
        print("  - Ensure the database is running: docker ps | grep postgres")
        print("  - Check if TEI service is running: docker ps | grep tei")
        print("  - Verify sample incidents are loaded: docker exec -it postgres psql -U agent_user -d agent_checkpoints -c 'SELECT COUNT(*) FROM incident_knowledge;'")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Query the RAG knowledge base for similar incidents")
    parser.add_argument("--query", default="Memory usage growing over time, eventually hitting limits", 
                        help="Query string to search for")
    parser.add_argument("--service", default="news-classifier-api", 
                        help="Service name to filter by (optional)")
    parser.add_argument("--top_k", type=int, default=3, 
                        help="Number of results to return")
    parser.add_argument("--similarity_threshold", type=float, default=0.6, 
                        help="Minimum similarity score (0.0-1.0)")
    
    args = parser.parse_args()
    main(query=args.query, service=args.service, top_k=args.top_k, 
         similarity_threshold=args.similarity_threshold)
