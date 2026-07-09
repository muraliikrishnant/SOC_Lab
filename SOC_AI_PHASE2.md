# SOC AI — Phase 2: GraphRAG Triage (Splunk / Elastic)

This is Phase 2 of the SOC/SOAR pipeline: a retrieval-augmented triage layer
on top of the existing Elastic+Ollama stack, adding Neo4j (graph) + Qdrant
(vector) grounding, Splunk as a second ingestion/write-back target, entity
extraction, structured LLM verdicts, and report generation. It does not
retrain any model — see the "what training actually means here" framing in
`soc_ai_build_plan.docx`; this grounds the existing Ollama model with
retrieval instead.

**Wazuh adapter is deferred** — not built yet. `soc_ai/soc_ai/adapters/`
has `splunk.py` and `elastic.py`; add a `wazuh.py` there later following
the same `normalize()` / `writeback()` / `poll()` shape and register it in
`adapters/__init__.py`.

## Architecture

```
Splunk (poll via REST API) ─┐
                             ├─→ adapter.normalize() → CommonAlert
Elasticsearch (poll)  ──────┘         │
                                       ▼
                              entity extraction (regex)
                                       │
                          ┌────────────┴────────────┐
                          ▼                          ▼
                     Neo4j (graph write)      Qdrant (vector write)
                          │                          │
                          └────────────┬─────────────┘
                                       ▼
                            retrieval (graph neighborhood
                             + vector top-k, capped)
                                       │
                                       ▼
                         Ollama LLM reasoning (hardened prompt)
                                       │
                                       ▼
                              structured Verdict
                          ┌────────────┴────────────┐
                          ▼                          ▼
                  adapter.writeback()         report.py (markdown:
                (Splunk HEC / ES index)        per-alert + shift digest)
```

Everything from entity extraction onward is SIEM-agnostic — it only ever
touches `CommonAlert`, never a raw Splunk/Elastic field name. The only
SIEM-specific code lives in `soc_ai/soc_ai/adapters/`.

## Prerequisites

- Docker Desktop (already installed)
- `soc_ai/splunk/default.yml` bootstraps Splunk's admin password + HEC
  token from `.env` on first boot — copy `.env.example` to `.env` and set
  real values before first `docker compose up`.
- Apple Silicon note: Splunk has no native arm64 image, so `docker-compose.yml`
  pins `platform: linux/amd64` for it — Docker Desktop runs it under
  emulation. It boots noticeably slower than the other services; give it a
  few minutes on first start.

## Bring it up

```bash
cd SOC_SIEM
cp .env.example .env   # edit passwords/tokens first
docker compose up -d
docker compose ps      # wait for neo4j, qdrant, splunk, soc-api healthy
```

Pull the models the pipeline needs (embeddings + reasoning):

```bash
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull mistral   # already used by alert_analyzer.py; swap to
                                                   # llama3.1:8b or qwen2.5:14b later via LLM_MODEL
                                                   # env var for stronger structured-output reasoning
```

Load the grounding knowledge (curated MITRE ATT&CK subset + Sigma-style
rules — see `soc_ai/soc_ai/seed/`) into Neo4j + Qdrant:

```bash
curl -X POST http://localhost:8080/seed
```

## Verify

```bash
curl http://localhost:8080/health
```

Expect `{"qdrant": true, "ollama": true, "elasticsearch": true, "splunk": true, "neo4j": true}`.
Splunk's REST API can take a few minutes to come up after the container
reports "running" — retry if `splunk: false` at first.

## Test the pipeline without waiting for a real alert

```bash
curl -X POST http://localhost:8080/ingest/splunk -H 'Content-Type: application/json' -d '{
  "_time": "'$(date +%s)'",
  "_raw": "Failed password for invalid user admin from 203.0.113.45 port 51322 ssh2",
  "host": "web01",
  "src_ip": "203.0.113.45",
  "user": "admin",
  "signature": "SSH Brute Force",
  "severity": "8"
}'
```

Returns the structured verdict + rendered markdown report. Check
`GET /report/digest?hours=1` afterward for the shift-digest view.

To test retrieval quality independent of the LLM (per the build plan's
Section 5, Phase 3 goal):

```bash
curl -X POST http://localhost:8080/retrieve/splunk -H 'Content-Type: application/json' -d '{...same body...}'
```

## Wiring Splunk/Elastic for real alerts

**Default: polling.** `soc-api` polls both Splunk (REST API search) and
Elasticsearch every `POLL_INTERVAL_SECONDS` (default 30s) — nothing to
configure, alerts flow automatically once indexed.

**Optional, lower latency:**
- **Splunk**: create a saved search → Alert → add a **Webhook** alert
  action pointed at `http://soc-api:8080/ingest/splunk` (or your host's
  reachable address). Fires the moment the search matches instead of
  waiting for the next poll.
- **Elastic/Kibana**: Security app → Detection rules → add a rule action
  using the **Webhook connector**, pointed at `.../ingest/elastic`.

## Reports

- Per-alert markdown report: returned inline from `/ingest/{source}` as
  `report_markdown`, and written back into the SIEM (Splunk HEC event /
  ES `soc-ai-verdicts` index) so it's visible next to the source alert.
- Shift digest: `GET /report/digest?hours=12` — one templated summary
  table plus a single batched LLM-generated narrative paragraph (not one
  LLM call per alert).

## Known limitations / next steps

- Wazuh adapter not built — see note above.
- Seed data (`soc_ai/soc_ai/seed/*.json`) is a curated starter set (~30
  ATT&CK techniques, ~15 Sigma-style rules), not the full MITRE STIX feed
  or SigmaHQ repo. `seed_data.py` is written so pointing it at more
  records later is a data change, not a code change.
- No eval harness yet (build plan Section 6) — build the 50–100 item
  hand-labeled set and score precision/recall against it once alerts are
  flowing for real.
