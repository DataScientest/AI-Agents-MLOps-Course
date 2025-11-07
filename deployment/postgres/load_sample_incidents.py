#!/usr/bin/env python3
"""Standalone script to load sample incidents into PostgreSQL with embeddings.

This script runs independently of the agent service and directly:
1. Reads incidents from CSV
2. Generates embeddings via TEI HTTP endpoint
3. Stores them in PostgreSQL with pgvector

Environment variables required:
- POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
- HUGGINGFACE_TEI_URL (default: http://tei:8080)
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg
import requests
from pgvector.psycopg import register_vector


def generate_embedding(text: str, tei_url: str) -> list[float]:
    """Generate embedding using TEI endpoint."""
    response = requests.post(
        tei_url,
        json={"inputs": [text]},
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    return response.json()[0]


def load_incidents_from_csv(csv_path: str) -> list[dict]:
    """Load incidents from CSV file."""
    incidents = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            incidents.append(row)
    return incidents


def main():
    """Load all sample incidents into knowledge base."""
    print("=" * 60)
    print("Loading Sample Incidents into Knowledge Base")
    print("=" * 60)

    # Get configuration from environment
    postgres_host = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_db = os.getenv("POSTGRES_DB", "agent_checkpoints")
    postgres_user = os.getenv("POSTGRES_USER", "agent_user")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "agent_password")
    tei_url = os.getenv("HUGGINGFACE_TEI_URL", "http://tei:8080")

    postgres_uri = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

    # Find CSV file
    csv_path = Path("/docker-entrypoint-initdb.d/data/sample_incidents.csv")
    if not csv_path.exists():
        csv_path = Path(__file__).parent.parent / "data" / "sample_incidents.csv"
    
    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    # Load incidents from CSV
    print(f"\nReading incidents from: {csv_path}")
    incidents = load_incidents_from_csv(str(csv_path))
    print(f"Loaded {len(incidents)} incidents from CSV")

    # Connect to PostgreSQL
    print("\nConnecting to PostgreSQL...")
    conn = psycopg.connect(postgres_uri)
    register_vector(conn)

    # Add each incident
    print(f"\nAdding incidents to knowledge base (using TEI at {tei_url})...")
    print("This will take ~30 seconds for embeddings generation...\n")
    
    with conn.cursor() as cur:
        for i, row in enumerate(incidents, 1):
            try:
                print(f"  [{i}/{len(incidents)}] {row['incident_id']}: {row['summary'][:50]}...")
                
                # Create text for embedding
                text_to_embed = f"{row['alert_type']} - {row['summary']} - {row['root_cause']} - {row['solution']}"
                
                # Generate embedding
                embedding = generate_embedding(text_to_embed, tei_url)
                
                # Insert into database
                cur.execute(
                    """
                    INSERT INTO incident_knowledge (
                        incident_id, service_name, alert_type, severity,
                        summary, root_cause, solution, embedding,
                        occurred_at, resolved_at, resolution_time_seconds
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (incident_id) DO NOTHING
                    RETURNING id
                    """,
                    (
                        row["incident_id"],
                        row["service_name"],
                        row["alert_type"],
                        row["severity"],
                        row["summary"],
                        row["root_cause"],
                        row["solution"],
                        embedding,
                        datetime.fromisoformat(row["occurred_at"]),
                        datetime.fromisoformat(row["resolved_at"]),
                        int(row["resolution_time_seconds"]),
                    ),
                )
                
                result = cur.fetchone()
                if result:
                    print(f"      ✓ Added with id={result[0]}")
                else:
                    print(f"      ℹ️  Already exists, skipped")
                    
            except Exception as e:
                print(f"      ✗ Error: {e}")
                continue

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("✓ Sample incidents loaded successfully!")
    print("=" * 60)
    print("\nYou can now use RAGKnowledgeSearch tool to retrieve similar incidents.")
    print("Example query: 'high CPU usage during deployment'")


if __name__ == "__main__":
    main()
