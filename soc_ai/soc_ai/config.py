import os


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


ELASTICSEARCH_URL = os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:1.5b")

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

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK", "")

POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))
RETRIEVAL_GRAPH_HOPS = int(os.environ.get("RETRIEVAL_GRAPH_HOPS", "2"))
RETRIEVAL_GRAPH_LIMIT = int(os.environ.get("RETRIEVAL_GRAPH_LIMIT", "5"))
RETRIEVAL_VECTOR_TOP_K = int(os.environ.get("RETRIEVAL_VECTOR_TOP_K", "5"))

DATA_DIR = os.environ.get("DATA_DIR", "/data")
