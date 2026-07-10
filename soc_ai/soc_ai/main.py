import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from . import chat as chat_module
from . import config, pipeline, seed_data, store
from .adapters import ADAPTERS
from .report import render_digest_report

_STATIC_DIR = Path(__file__).parent / "static"

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_poller_tasks: list[asyncio.Task] = []


async def _poll_loop(source: str):
    adapter = ADAPTERS[source]
    since: Optional[float] = None
    log.info("Starting poller for %s (interval=%ss)", source, config.POLL_INTERVAL_SECONDS)
    while True:
        try:
            raw_events, since = await asyncio.to_thread(adapter.poll, since)
            for raw in raw_events:
                try:
                    await asyncio.to_thread(pipeline.process_alert, source, raw)
                except Exception:
                    log.exception("Failed to process %s alert", source)
        except Exception:
            log.exception("Poller for %s crashed this cycle", source)
        await asyncio.sleep(config.POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for source in ADAPTERS:
        _poller_tasks.append(asyncio.create_task(_poll_loop(source)))
    yield
    for task in _poller_tasks:
        task.cancel()


app = FastAPI(title="SOC AI GraphRAG Triage", lifespan=lifespan)


@app.post("/ingest/{source}")
async def ingest(source: str, raw: dict):
    """Push endpoint — point a Splunk webhook alert action or Kibana
    webhook connector here for immediate (non-polled) ingestion."""
    if source not in ADAPTERS:
        raise HTTPException(404, f"unknown source '{source}', expected one of {list(ADAPTERS)}")
    try:
        verdict, markdown = await asyncio.to_thread(pipeline.process_alert, source, raw)
    except Exception as exc:
        log.exception("Ingest failed")
        raise HTTPException(500, str(exc))
    return {"verdict": verdict, "report_markdown": markdown}


@app.post("/retrieve/{source}")
async def retrieve_only(source: str, raw: dict):
    """Normalize + extract entities + retrieve context, without invoking
    the LLM — for testing retrieval quality independent of reasoning."""
    if source not in ADAPTERS:
        raise HTTPException(404, f"unknown source '{source}', expected one of {list(ADAPTERS)}")
    from . import retrieval
    from .entities import extract_entities

    adapter = ADAPTERS[source]
    alert = await asyncio.to_thread(adapter.normalize, raw)
    entities = extract_entities(alert)
    ctx = await asyncio.to_thread(retrieval.retrieve, alert, entities)
    return {"alert": alert, "entities": entities, "context": ctx}


@app.get("/report/digest", response_class=PlainTextResponse)
async def digest_report(hours: float = 12):
    verdicts = store.recent(since_seconds=hours * 3600)
    return await asyncio.to_thread(render_digest_report, verdicts)


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@app.get("/chat/ui")
async def chat_ui():
    """Chat page meant to be embedded as an iframe panel inside a Splunk
    dashboard (see soc_ai/splunk/apps/soc_ai_chat) so an analyst can talk
    to the AI while looking at search results."""
    return FileResponse(_STATIC_DIR / "chat.html")


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        return await asyncio.to_thread(chat_module.chat, req.message, req.history)
    except requests.RequestException as exc:
        raise HTTPException(502, f"Ollama chat call failed: {exc}")


@app.post("/seed")
async def seed():
    result = await asyncio.to_thread(seed_data.run)
    return result


@app.get("/health")
async def health():
    checks = {}
    try:
        r = requests.get(f"{config.QDRANT_URL}/collections", timeout=5)
        checks["qdrant"] = r.ok
    except requests.RequestException:
        checks["qdrant"] = False
    try:
        r = requests.get(f"{config.OLLAMA_URL}/api/tags", timeout=5)
        checks["ollama"] = r.ok
    except requests.RequestException:
        checks["ollama"] = False
    try:
        r = requests.get(f"{config.ELASTICSEARCH_URL}", timeout=5)
        checks["elasticsearch"] = r.ok
    except requests.RequestException:
        checks["elasticsearch"] = False
    try:
        r = requests.get(
            f"{config.SPLUNK_URL}/services/server/info",
            auth=(config.SPLUNK_USER, config.SPLUNK_PASSWORD),
            verify=config.SPLUNK_VERIFY_TLS,
            timeout=5,
        )
        checks["splunk"] = r.ok
    except requests.RequestException:
        checks["splunk"] = False
    from . import graph

    try:
        with graph.get_driver().session() as s:
            s.run("RETURN 1")
        checks["neo4j"] = True
    except Exception:
        checks["neo4j"] = False
    return checks
