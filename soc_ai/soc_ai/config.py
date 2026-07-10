import os


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

# Reasoning/chat model runs on Ollama Cloud, not the local container — any
# model tagged "*:cloud" is routed by reasoning.py / chat.py to the
# https://ollama.com API with OLLAMA_API_KEY as a bearer token instead of
# the local OLLAMA_URL. Only embeddings run against the local container.
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4:cloud")
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_CLOUD_URL = os.environ.get("OLLAMA_CLOUD_URL", "https://ollama.com")

NEO4J_URL = os.environ.get("NEO4J_URL", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "changeme123")

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "soc_knowledge")

SPLUNK_URL = os.environ.get("SPLUNK_URL", "https://localhost:8089")
SPLUNK_HEC_URL = os.environ.get("SPLUNK_HEC_URL", "https://localhost:8088")
SPLUNK_HEC_TOKEN = os.environ.get("SPLUNK_HEC_TOKEN", "soc-ai-hec-token")
SPLUNK_USER = os.environ.get("SPLUNK_USER", "admin")
SPLUNK_PASSWORD = os.environ.get("SPLUNK_PASSWORD", "Changeme123!")
SPLUNK_VERIFY_TLS = _bool("SPLUNK_VERIFY_TLS", False)
SPLUNK_SEARCH_INDEX = os.environ.get("SPLUNK_SEARCH_INDEX", "*")

# How far back chat's live-search looks by default. Wide on purpose: this
# lab mixes live alerts with bulk-imported historical datasets (e.g. a CSV
# backfilled with 2024 timestamps), and a tight "-24h" window silently
# hides all of that with no indication why nothing was found.
CHAT_SEARCH_EARLIEST = os.environ.get("CHAT_SEARCH_EARLIEST", "-5y")

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))
RETRIEVAL_GRAPH_HOPS = int(os.environ.get("RETRIEVAL_GRAPH_HOPS", "2"))
RETRIEVAL_GRAPH_LIMIT = int(os.environ.get("RETRIEVAL_GRAPH_LIMIT", "5"))
RETRIEVAL_VECTOR_TOP_K = int(os.environ.get("RETRIEVAL_VECTOR_TOP_K", "5"))

DATA_DIR = os.environ.get("DATA_DIR", "/data")
