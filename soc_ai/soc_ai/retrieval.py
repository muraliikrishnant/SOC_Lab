"""Retrieval layer: given a new alert, pull the graph neighborhood + vector
top-k and merge into one bounded context object. The caps here
(RETRIEVAL_GRAPH_LIMIT / RETRIEVAL_VECTOR_TOP_K) are the actual lever on
LLM latency and token cost — retrieval breadth, not model choice.
"""
from . import config, graph, vectorstore
from .schema import CommonAlert, Entities, RetrievalContext


def build_query_text(alert: CommonAlert) -> str:
    parts = [alert.rule_name or "", alert.raw_log[:500]]
    return " ".join(p for p in parts if p)


def retrieve(alert: CommonAlert, entities: Entities) -> RetrievalContext:
    query_text = build_query_text(alert)
    query_vector = vectorstore.embed(query_text)

    related_alerts = graph.neighborhood(
        alert.id, hops=config.RETRIEVAL_GRAPH_HOPS, limit=config.RETRIEVAL_GRAPH_LIMIT
    )
    matched_techniques = graph.matched_techniques(alert.id, limit=3)

    # One embedding call, reused across all three type-filtered searches.
    similar_past_alerts = vectorstore.search_by_vector(
        query_vector, top_k=config.RETRIEVAL_VECTOR_TOP_K, type_filter="alert"
    )
    matched_sigma_rules = vectorstore.search_by_vector(query_vector, top_k=3, type_filter="sigma")
    technique_hits = vectorstore.search_by_vector(query_vector, top_k=3, type_filter="technique")

    # Merge graph-matched and vector-matched techniques, de-duplicated by id.
    seen = {t["id"] for t in matched_techniques}
    for hit in technique_hits:
        tid = hit.get("technique_id") or hit.get("natural_id")
        if tid and tid not in seen:
            matched_techniques.append({"id": tid, "name": hit.get("name"), "description": hit.get("description")})
            seen.add(tid)

    return RetrievalContext(
        related_alerts=related_alerts,
        matched_techniques=matched_techniques,
        matched_sigma_rules=matched_sigma_rules,
        similar_past_alerts=similar_past_alerts,
    )
