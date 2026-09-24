"""Application settings and environment configuration."""

import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class Settings:
  """Application configuration settings."""

  # LLM settings
  OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
  MODEL: str = os.getenv("MODEL", "chatgpt-4.1-mini")
  BASE_URL: str = os.getenv("BASE_URL", "https://api.openrouter.ai/v1")

  # Per-role token ceilings
  MAX_TOKENS_ROUTER: int = int(os.getenv("MAX_TOKENS_ROUTER", "200"))
  MAX_TOKENS_SUPERVISOR: int = int(os.getenv("MAX_TOKENS_SUPERVISOR", "400"))
  MAX_TOKENS_AGENT: int = int(os.getenv("MAX_TOKENS_AGENT", "1200"))
  MAX_TOKENS_CREW_AGENT: int = int(os.getenv("MAX_TOKENS_CREW_AGENT", "1200"))
  MAX_TOKENS_DEEP_AGENT: int = int(os.getenv("MAX_TOKENS_DEEP_AGENT", "1500"))
  MAX_TOKENS_SUMMARY: int = int(os.getenv("MAX_TOKENS_SUMMARY", "900"))

  # Storage paths
  DATA_DIR: str = os.getenv("DATA_DIR", "./data")
  POLICY_DOCS_DIR: str = os.getenv(DATA_DIR, "policy_docs")
  SQLITE_DB_PATH: str = os.getenv(
      "SQLITE_DB_PATH", "./data/commerceopsai.db"
  )
  CHECKPOINT_DB_PATH: str = os.getenv(
      "CHECKPOINT_DB_PATH", "./data/checkpoints.db"
  )
  CHROMA_DIR: str = os.getenv("CHROMA_DIR", "./data/chroma")
  KNOWLEDGE_GRAPH_PATH: str = os.getenv(
      "KNOWLEDGE_GRAPH_PATH", "./data/knowledge_graph.json"
  )
  INTENT_ROUTER_MODEL_PATH: str = os.getenv(
      "INTENT_ROUTER_MODEL_PATH", "./data/intent_router.joblib"
  )
  MCP_SQLITE_DB_PATH: str = os.getenv(
      "MCP_SQLITE_DB_PATH", "./data/commerceops.db"
  )

  #Redis
  REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
  JOB_QUEUE_NAME: str = "commerceops:jobs:queue"
  USE_REDIS_CHECKPOINTER: bool = (
      os.getenv("USE_REDIS_CHECKPOINTER", "false").lower() == "true"
  )

  # --- RAG Settings ---
  EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
  POLICY_COLLECTION: str = "policy_docs"
  RETRIEVER_TOP_K: int = int(os.getenv("RETRIEVER_TOP_K", "5"))
  CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "700"))
  CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
  RAGAS_FAITHFULNESS_THRESHOLD: float = float(
      os.getenv("RAGAS_FAITHFULNESS_THRESHOLD", "0.90")
  )

  # --- Guardrails ---
  NEMO_CONFIG_DIR: str = os.getenv(
      "NEMO_CONFIG_DIR", "./app/guardrails/nemo_config"
  )
  PII_ENTITIES_TO_REDACT: tuple[str, ...] = (
      "PERSON",
      "EMAIL_ADDRESS",
      "PHONE_NUMBER",
      "US_SSN",
      "CREDIT_CARD",
      "IBAN_CODE",
      "US_BANK_NUMBER",
      "LOCATION",
  )
  COST_DATA_PATTERNS: tuple[str, ...] = (
      r"wholesale\s+cost",
      r"cost\s+basis",
      r"unit\s+cost",
      r"margin\s+percent",
      r"supplier\s+price",
  )

  # --- HITL / Risk Thresholds ---
  REFUND_APPROVAL_THRESHOLD: float = float(
      os.getenv("REFUND_APPROVAL_THRESHOLD", "250.0")
  )

  ## --- Observability ---
  LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
  LANGCHAIN_PROJECT: str = os.getenv("LANGCHAIN_PROJECT", "commerceops-ai")
  PHOENIX_ENABLED: bool = (
      os.getenv("PHOENIX_ENABLED", "false").lower() == "true"
  )
  PHOENIX_COLLECTOR_ENDPOINT: str = os.getenv(
      "PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces"
  )
  OTEL_EXPORTER_PROMETHEUS_PORT: int = int(
      os.getenv("OTEL_EXPORTER_PROMETHEUS_PORT", "9464")
  )
  WORKER_METRICS_PORT: int = int(os.getenv("WORKER_METRICS_PORT", "9100"))
  
  # --- App Settings ---
  APP_ENV: str = os.getenv("APP_ENV", "development")
  API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
  API_PORT: int = int(os.getenv("API_PORT", "8000"))
  CORS_ORIGINS: tuple[str, ...] = tuple(
      origin.strip()
      for origin in os.getenv("CORS_ORIGINS", "*").split(",")
      if origin.strip()
  )

settings = Settings()

if os.getenv("LANGSMITH_API_KEY"):
  os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.LANGCHAIN_TRACING_V2)
  os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT)
  



