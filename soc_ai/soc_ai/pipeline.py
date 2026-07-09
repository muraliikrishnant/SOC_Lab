"""Orchestrates one alert end to end: normalize -> extract entities ->
graph write -> vector write -> retrieve -> reason -> report -> write back
-> store. This is the single place that ties every module together; each
module stays independently testable (e.g. hit /retrieve directly without
invoking the LLM).
"""
import logging

from . import graph, report, retrieval, store, vectorstore
from .adapters import ADAPTERS
from .entities import extract_entities
from .reasoning import reason
from .schema import CommonAlert, Verdict

log = logging.getLogger(__name__)


def process_alert(source: str, raw: dict) -> tuple[Verdict, str]:
    adapter = ADAPTERS[source]
    alert: CommonAlert = adapter.normalize(raw)
    entities = extract_entities(alert)

    graph.upsert_alert(alert, entities)
    vectorstore.upsert(
        alert.id,
        f"{alert.rule_name or ''} {alert.raw_log[:1000]}",
        {"type": "alert", "rule_name": alert.rule_name, "severity": alert.severity, "host": alert.host},
    )

    ctx = retrieval.retrieve(alert, entities)
    verdict = reason(alert, ctx)

    adapter.writeback(verdict)
    store.append(verdict)

    # Feedback loop: store the confirmed verdict's severity/technique back
    # onto the alert node so future graph neighborhood queries see it too.
    alert.severity = verdict.severity
    alert.mitre_technique = verdict.mitre_technique or alert.mitre_technique
    graph.upsert_alert(alert, entities)

    markdown = report.render_alert_report(verdict)
    return verdict, markdown
