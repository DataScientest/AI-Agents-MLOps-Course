#!/bin/bash
# PostgreSQL data loading script
# Runs after init.sql to load sample incidents with embeddings
# This script is executed by a separate container, not by postgres itself

set -e

echo "📚 PostgreSQL Sample Data Loader"
echo "================================"

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $POSTGRES_DB -c '\q' 2>/dev/null; do
    echo "   PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# Wait for TEI to be ready
echo "⏳ Waiting for TEI embeddings service..."
until curl -s http://tei:8080/health > /dev/null 2>&1; do
    echo "   TEI is unavailable - sleeping"
    sleep 2
done
echo "✅ TEI is ready!"

# Check if data already loaded
COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h postgres -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM incident_knowledge;" 2>/dev/null || echo "0")
COUNT=$(echo $COUNT | tr -d ' ')

if [ "$COUNT" -gt "0" ]; then
    echo "ℹ️  Sample data already loaded ($COUNT incidents found)"
    exit 0
fi

# Load sample incidents
echo "📥 Loading sample incidents into knowledge base..."
python3 /docker-entrypoint-initdb.d/load_sample_incidents.py

echo "✅ Sample data loading complete!"
