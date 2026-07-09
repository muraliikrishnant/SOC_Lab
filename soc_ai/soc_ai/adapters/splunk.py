"""Splunk adapter: normalize search results into CommonAlert, write verdicts
back via HTTP Event Collector (HEC), and poll via the Splunk REST API.

Polling (rather than requiring you to hand-configure a webhook alert action
in Splunk's UI first) is the default here so the pipeline works the moment
Splunk is reachable. A webhook alert action pointed at POST /ingest/splunk
is a lower-latency upgrade you can wire up later (see README) — once
configured, alerts arrive immediately instead of on the next poll tick.
"""
import json
import logging
import time
from typing import Optional

import requests

from .. import config
from ..schema import CommonAlert, Verdict

log = logging.getLogger(__name__)

_severity_map = {
    "1": "low", "2": "low", "3": "low",
    "4": "medium", "5": "medium", "6": "medium",
    "7": "high", "8": "high",
    "9": "critical", "10": "critical",
}


def _map_severity(raw) -> str:
    if raw is None:
        return "unknown"
    s = str(raw).strip().lower()
    if s in ("low", "medium", "high", "critical"):
        return s
    return _severity_map.get(s, "unknown")


def normalize(raw: dict) -> CommonAlert:
    fields = raw.get("_raw_fields", raw)
    natural_key = raw.get("_cd") or raw.get("_time") or raw.get("_raw", "")[:64]
    return CommonAlert(
        id=CommonAlert.make_id("splunk", str(natural_key)),
        source_system="splunk",
        timestamp=_parse_time(raw.get("_time")),
        host=fields.get("host") or raw.get("host"),
        user=fields.get("user") or fields.get("src_user"),
        src_ip=fields.get("src_ip") or fields.get("src"),
        dest_ip=fields.get("dest_ip") or fields.get("dest"),
        process=fields.get("process") or fields.get("process_name"),
        hash=fields.get("file_hash") or fields.get("hash"),
        rule_name=fields.get("signature") or fields.get("search_name") or raw.get("sourcetype"),
        severity=_map_severity(fields.get("severity") or fields.get("urgency")),
        raw_log=raw.get("_raw", ""),
        raw=raw,
    )


def _parse_time(value) -> float:
    if not value:
        return time.time()
    try:
        return float(value)
    except (TypeError, ValueError):
        return time.time()


def writeback(verdict: Verdict) -> bool:
    """Write the AI verdict back into Splunk as a HEC event, correlated to
    the source alert via alert_id so it shows up next to the original."""
    url = f"{config.SPLUNK_HEC_URL}/services/collector/event"
    headers = {"Authorization": f"Splunk {config.SPLUNK_HEC_TOKEN}"}
    payload = {
        "sourcetype": "soc:ai:verdict",
        "event": verdict.model_dump(),
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, verify=config.SPLUNK_VERIFY_TLS, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        log.warning("Splunk HEC write-back failed: %s", exc)
        return False


def poll(since: Optional[float]) -> tuple[list[dict], Optional[float]]:
    """Pull recent events via the Splunk REST API (oneshot search export).
    Returns (raw_events, new_since_cursor)."""
    earliest = "-5m" if since is None else f"{since}"
    # Exclude our own write-back sourcetype, or the poller re-ingests the
    # AI's verdicts as if they were new alerts and re-triages them forever.
    spl = (
        f'search index={config.SPLUNK_SEARCH_INDEX} earliest={earliest} sourcetype!="soc:ai:verdict" '
        f"| sort - _time | head 100"
    )
    url = f"{config.SPLUNK_URL}/services/search/jobs/export"
    try:
        resp = requests.post(
            url,
            auth=(config.SPLUNK_USER, config.SPLUNK_PASSWORD),
            data={"search": spl, "output_mode": "json", "exec_mode": "oneshot"},
            verify=config.SPLUNK_VERIFY_TLS,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Splunk poll failed: %s", exc)
        return [], since

    events = []
    latest_time = since or 0.0
    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except ValueError:
            continue
        result = doc.get("result")
        if not result:
            continue
        events.append(result)
        try:
            latest_time = max(latest_time, float(result.get("_time", latest_time)))
        except (TypeError, ValueError):
            pass
    return events, (latest_time or None)
