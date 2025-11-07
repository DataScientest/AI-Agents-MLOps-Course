# PostgreSQL Deployment for Chapter 4

This folder contains PostgreSQL initialization and data loading scripts for the AIOps Agent knowledge base.

## Files

### `init.sql`
- **Purpose**: Database schema initialization
- **When it runs**: Automatically on first PostgreSQL container startup
- **What it does**:
  - Creates `pgvector` extension for vector similarity search
  - Creates `incident_knowledge` table with embedding column
  - Creates `diagnosis_feedback` table for learning
  - Creates `alert_type_stats` table for confidence tracking
  - Sets up indexes for fast similarity search

### `load_sample_incidents.py`
- **Purpose**: Standalone Python script to load sample incidents
- **Dependencies**: `psycopg`, `pgvector`, `requests`
- **What it does**:
  1. Reads 20 sample incidents from `data/sample_incidents.csv`
  2. Generates embeddings via TEI HTTP endpoint
  3. Stores incidents with embeddings in PostgreSQL
  4. Checks for duplicates before inserting

### `load_sample_data.sh`
- **Purpose**: Bash wrapper script for data loading
- **What it does**:
  1. Waits for PostgreSQL to be ready
  2. Waits for TEI embeddings service to be ready
  3. Checks if data already exists (prevents duplicates)
  4. Runs `load_sample_incidents.py`

### `Dockerfile.loader`
- **Purpose**: Docker image for the data-loader service
- **Base image**: `python:3.12-slim`
- **Installed**: PostgreSQL client, Python dependencies
- **Entry point**: `load_sample_data.sh`

## Usage

### Load Sample Data

From the project root:

```bash
docker compose --profile tools up data-loader
```

This will:
- Build the data-loader image
- Wait for dependencies (postgres, tei)
- Load 20 sample incidents
- Exit automatically

### Verify Data

```bash
docker exec postgres psql -U agent_user -d agent_checkpoints -c \
  "SELECT COUNT(*) FROM incident_knowledge;"
```

Should return `20`.

### Query Sample Data

```bash
docker exec postgres psql -U agent_user -d agent_checkpoints -c \
  "SELECT incident_id, service_name, alert_type, summary FROM incident_knowledge LIMIT 5;"
```

## Architecture Benefits

1. **Separation of Concerns**: Data loading is separate from the agent service
2. **Idempotent**: Can run multiple times without duplicating data
3. **Independent**: Doesn't require agent code dependencies
4. **Fast**: Runs once and exits, doesn't consume resources
5. **Clean**: Uses Docker profiles to avoid running on every startup

## Environment Variables

Required for `data-loader` service:
- `POSTGRES_HOST` - PostgreSQL host (default: postgres)
- `POSTGRES_PORT` - PostgreSQL port (default: 5432)
- `POSTGRES_DB` - Database name (default: agent_checkpoints)
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password
- `HUGGINGFACE_TEI_URL` - TEI endpoint URL (default: http://tei:8080)
