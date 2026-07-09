"""Elastic adapter: normalize Elasticsearch documents into CommonAlert,
write verdicts back into a dedicated index, and poll via the ES search API.

Today's filebeat.yml ships raw syslog text (no Wazuh module parsing), so a
doc from `logs-*` is just {"@timestamp", "message", "host", ...}.

If you later add a Kibana detection rule with a webhook connector pointed
at POST /ingest/elastic, alerts arrive the moment a rule fires instead of
on the next poll tick — polling here is what works without that extra
manual UI setup.
"""
import logging
import time
from typing import Optional

import requests

from .. import config
from ..schema import CommonAlert, Verdict

log = logging.getLogger(__name__)
VERDICT_INDEX = "soc-ai-verdicts"


def search_recent(index: str, since_ts: Optional[float], size: int = 100) -> list[dict]:
    since_iso = None
    if since_ts:
        since_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(since_ts))
    query = {
        "size": size,
        "sort": [{"@timestamp": {"order": "asc"}}],
        "query": (
            {"range": {"@timestamp": {"gt": since_iso}}}
            if since_iso
            else {"match_all": {}}
        ),
    }
    try:
        resp = requests.post(f"{config.ELASTICSEARCH_URL}/{index}/_search", json=query, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Elasticsearch query failed: %s", exc)
        return []
    return [hit["_source"] for hit in resp.json().get("hits", {}).get("hits", [])]


def normalize(raw: dict) -> CommonAlert:
    natural_key = raw.get("@timestamp", "") + raw.get("message", "")[:64]
    return CommonAlert(
        id=CommonAlert.make_id("elastic", natural_key),
        source_system="elastic",
        timestamp=_parse_iso(raw.get("@timestamp")),
        host=(raw.get("host") or {}).get("name") if isinstance(raw.get("host"), dict) else raw.get("host"),
        rule_name=raw.get("event", {}).get("action") if isinstance(raw.get("event"), dict) else None,
        severity="unknown",
        raw_log=raw.get("message", ""),
        raw=raw,
    )


def _parse_iso(value) -> float:
    if not value:
        return time.time()
    try:
        return time.mktime(time.strptime(value[:19], "%Y-%m-%dT%H:%M:%S"))
    except (TypeError, ValueError):
        return time.time()


def writeback(verdict: Verdict) -> bool:
    """Index the AI verdict into a dedicated ES index so it's viewable
    alongside the source alert in Kibana."""
    url = f"{config.ELASTICSEARCH_URL}/{VERDICT_INDEX}/_doc"
    try:
        resp = requests.post(url, json=verdict.model_dump(), timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.warning("Elasticsearch verdict write-back failed: %s", exc)
        return False


def poll(since: Optional[float]) -> tuple[list[dict], Optional[float]]:
    docs = search_recent("logs-*", since)
    new_since = since
    for d in docs:
        ts = _parse_iso(d.get("@timestamp"))
        new_since = ts if new_since is None else max(new_since, ts)
    return docs, new_since
