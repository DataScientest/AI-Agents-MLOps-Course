-- PostgreSQL initialization script for AIOps Agent
-- Creates pgvector extension and knowledge base schema
-- This runs automatically when the container first starts

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Knowledge Base: Incident History Table
-- Stores past incidents with embeddings for RAG retrieval
CREATE TABLE IF NOT EXISTS incident_knowledge (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(100) UNIQUE NOT NULL,

    -- Core incident information
    service_name VARCHAR(255) NOT NULL,
    alert_type VARCHAR(255) NOT NULL,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),

    -- Incident details
    summary TEXT NOT NULL,
    root_cause TEXT NOT NULL,
    solution TEXT NOT NULL,

    -- Vector embedding for semantic search
    -- OpenAI ada-002 = 1536 dimensions
    -- HuggingFace bge-small-en-v1.5 = 384 dimensions
    embedding vector(384),  -- Change based on your embedding model

    -- Metadata for filtering and analysis
    occurred_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolution_time_seconds INTEGER,

    -- Learning and confidence tracking
    times_referenced INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    confidence_score FLOAT DEFAULT 0.0,

    -- Versioning
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast similarity search
CREATE INDEX IF NOT EXISTS incident_embedding_idx ON incident_knowledge
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for metadata filtering
CREATE INDEX IF NOT EXISTS incident_service_idx ON incident_knowledge(service_name);
CREATE INDEX IF NOT EXISTS incident_alert_type_idx ON incident_knowledge(alert_type);
CREATE INDEX IF NOT EXISTS incident_severity_idx ON incident_knowledge(severity);
CREATE INDEX IF NOT EXISTS incident_occurred_idx ON incident_knowledge(occurred_at DESC);

-- Diagnosis Feedback Table
-- Tracks agent diagnosis outcomes for continuous learning
CREATE TABLE IF NOT EXISTS diagnosis_feedback (
    id SERIAL PRIMARY KEY,
    diagnosis_id VARCHAR(100) UNIQUE NOT NULL,
    thread_id VARCHAR(255) NOT NULL,

    -- What was diagnosed
    alert_info TEXT NOT NULL,
    service_name VARCHAR(255),
    alert_type VARCHAR(255),

    -- Agent's diagnosis
    proposed_root_cause TEXT,
    proposed_solution TEXT,
    confidence_score FLOAT,

    -- Human feedback
    outcome VARCHAR(50) CHECK (outcome IN ('success', 'partial_success', 'failure', 'escalated')),
    human_correction TEXT,
    corrected_root_cause TEXT,
    corrected_solution TEXT,

    -- Metadata
    diagnosed_at TIMESTAMP DEFAULT NOW(),
    feedback_received_at TIMESTAMP,

    -- Link to incident knowledge (if added to KB)
    incident_knowledge_id INTEGER REFERENCES incident_knowledge(id)
);

-- Index for tracking diagnoses by service and time
CREATE INDEX IF NOT EXISTS feedback_service_idx ON diagnosis_feedback(service_name);
CREATE INDEX IF NOT EXISTS feedback_thread_idx ON diagnosis_feedback(thread_id);
CREATE INDEX IF NOT EXISTS feedback_diagnosed_at_idx ON diagnosis_feedback(diagnosed_at DESC);

-- Alert Type Statistics Table
-- Aggregates success rates per alert type for confidence scoring
CREATE TABLE IF NOT EXISTS alert_type_stats (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(255) NOT NULL,
    alert_type VARCHAR(255) NOT NULL,

    -- Success tracking
    total_diagnoses INTEGER DEFAULT 0,
    successful_diagnoses INTEGER DEFAULT 0,
    failed_diagnoses INTEGER DEFAULT 0,
    escalated_diagnoses INTEGER DEFAULT 0,

    -- Performance metrics
    avg_resolution_time_seconds FLOAT,
    confidence_score FLOAT DEFAULT 0.0,

    -- Timestamps
    last_updated TIMESTAMP DEFAULT NOW(),

    -- Unique constraint
    UNIQUE(service_name, alert_type)
);

-- Function to update alert type stats automatically
CREATE OR REPLACE FUNCTION update_alert_type_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update if feedback has been provided
    IF NEW.outcome IS NOT NULL THEN
        INSERT INTO alert_type_stats (service_name, alert_type, total_diagnoses, successful_diagnoses, failed_diagnoses, escalated_diagnoses, last_updated)
        VALUES (
            NEW.service_name,
            NEW.alert_type,
            1,
            CASE WHEN NEW.outcome IN ('success', 'partial_success') THEN 1 ELSE 0 END,
            CASE WHEN NEW.outcome = 'failure' THEN 1 ELSE 0 END,
            CASE WHEN NEW.outcome = 'escalated' THEN 1 ELSE 0 END,
            NOW()
        )
        ON CONFLICT (service_name, alert_type) DO UPDATE SET
            total_diagnoses = alert_type_stats.total_diagnoses + 1,
            successful_diagnoses = alert_type_stats.successful_diagnoses +
                CASE WHEN NEW.outcome IN ('success', 'partial_success') THEN 1 ELSE 0 END,
            failed_diagnoses = alert_type_stats.failed_diagnoses +
                CASE WHEN NEW.outcome = 'failure' THEN 1 ELSE 0 END,
            escalated_diagnoses = alert_type_stats.escalated_diagnoses +
                CASE WHEN NEW.outcome = 'escalated' THEN 1 ELSE 0 END,
            confidence_score = CASE
                WHEN (alert_type_stats.total_diagnoses + 1) > 0 THEN
                    (alert_type_stats.successful_diagnoses + CASE WHEN NEW.outcome IN ('success', 'partial_success') THEN 1 ELSE 0 END)::FLOAT / (alert_type_stats.total_diagnoses + 1)
                ELSE 0.0
            END,
            last_updated = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update stats when feedback is added
CREATE TRIGGER update_stats_on_feedback
AFTER INSERT OR UPDATE OF outcome ON diagnosis_feedback
FOR EACH ROW
EXECUTE FUNCTION update_alert_type_stats();

-- Grant permissions (assumes POSTGRES_USER from environment)
-- Note: In production, use more restrictive permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agent_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agent_user;
