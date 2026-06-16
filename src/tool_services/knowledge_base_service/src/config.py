"""Configuration module for AIOps Agent Monitor.

This module centralizes all configuration, making it easy to switch between:
- Chapter 4: Monolithic deployment (direct database/service access)
- Chapter 5: Microservices deployment (HTTP service calls)

All configuration uses environment variables with sensible defaults.
"""

import os
from typing import Literal

# Deployment mode: "monolith" or "microservices"
DEPLOYMENT_MODE: Literal["monolith", "microservices"] = os.getenv(
    "DEPLOYMENT_MODE", "monolith"
)

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "mixtral-8x7b-32768")

# LangSmith Tracing
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "AIOps Monitor Agent")

# PostgreSQL Configuration (for checkpoints and knowledge base)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "agent_checkpoints")
POSTGRES_USER = os.getenv("POSTGRES_USER", "agent_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "agent_password")

# Build PostgreSQL connection string
POSTGRES_URI = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Monitoring Stack URLs (Chapter 3 tools)
# In Chapter 4: Direct access to monitoring services
# In Chapter 5: These point to tool microservices
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
GRAFANA_URL = os.getenv("GRAFANA_URL", "http://grafana:3000")

# Knowledge Base Configuration (Chapter 4 - Part 2)
# URL for knowledge base access (direct DB or HTTP service)
KNOWLEDGE_BASE_URL = os.getenv("KNOWLEDGE_BASE_URL", POSTGRES_URI)

# Embedding API Configuration
# Supports: "openai" (paid), "huggingface-tei" (free, self-hosted)
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "huggingface-tei")

# OpenAI configuration (if using openai provider)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1"

# Hugging Face TEI configuration (if using huggingface-tei provider)
HUGGINGFACE_TEI_URL = os.getenv("HUGGINGFACE_TEI_URL", "http://tei:8080")

# Model and dimensions (provider-specific defaults)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))

# RAG Configuration
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))  # Number of similar incidents to retrieve
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.7"))

# Feedback and Learning Configuration (Chapter 4 - Part 3)
CONFIDENCE_THRESHOLD_AUTO_REMEDIATE = float(
    os.getenv("CONFIDENCE_THRESHOLD_AUTO_REMEDIATE", "0.85")
)
CONFIDENCE_THRESHOLD_ESCALATE = float(
    os.getenv("CONFIDENCE_THRESHOLD_ESCALATE", "0.50")
)

# Agent API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8005"))


def get_config_summary() -> dict:
    """Returns a summary of current configuration (for debugging/logging)."""
    return {
        "deployment_mode": DEPLOYMENT_MODE,
        "llm_model": GROQ_MODEL_NAME,
        "postgres_host": POSTGRES_HOST,
        "embedding_provider": EMBEDDING_PROVIDER,
        "embedding_model": EMBEDDING_MODEL,
        "rag_top_k": RAG_TOP_K,
        "confidence_auto_remediate": CONFIDENCE_THRESHOLD_AUTO_REMEDIATE,
        "confidence_escalate": CONFIDENCE_THRESHOLD_ESCALATE,
    }
