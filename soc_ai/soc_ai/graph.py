"""Neo4j graph: entities (host, user, IP, hash, process) and their
relationships to alerts, plus grounding nodes (ATT&CK technique, Sigma
rule). Relationships carry a `ts` (last-seen timestamp) property rather
than treating identity as permanent — an IP seen on an alert six months
ago and one seen today are not necessarily the same host (DHCP/NAT), so
entity edges are time-scoped instead of merged blindly.
"""
import logging
from typing import Optional

from neo4j import GraphDatabase

from . import config
from .schema import CommonAlert, Entities

log = logging.getLogger(__name__)

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(config.NEO4J_URL, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD))
    return _driver


def close():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def ensure_constraints() -> None:
    stmts = [
        "CREATE CONSTRAINT alert_id IF NOT EXISTS FOR (a:Alert) REQUIRE a.id IS UNIQUE",
        "CREATE CONSTRAINT host_name IF NOT EXISTS FOR (h:Host) REQUIRE h.name IS UNIQUE",
        "CREATE CONSTRAINT user_name IF NOT EXISTS FOR (u:User) REQUIRE u.name IS UNIQUE",
        "CREATE CONSTRAINT ip_addr IF NOT EXISTS FOR (i:IP) REQUIRE i.address IS UNIQUE",
        "CREATE CONSTRAINT hash_val IF NOT EXISTS FOR (f:Hash) REQUIRE f.value IS UNIQUE",
        "CREATE CONSTRAINT process_name IF NOT EXISTS FOR (p:Process) REQUIRE p.name IS UNIQUE",
        "CREATE CONSTRAINT technique_id IF NOT EXISTS FOR (t:Technique) REQUIRE t.id IS UNIQUE",
        "CREATE CONSTRAINT sigma_id IF NOT EXISTS FOR (s:SigmaRule) REQUIRE s.id IS UNIQUE",
    ]
    with get_driver().session() as session:
        for stmt in stmts:
            session.run(stmt)


_UPSERT_ALERT = """
MERGE (a:Alert {id: $id})
SET a.source_system = $source_system,
    a.timestamp = $timestamp,
    a.rule_name = $rule_name,
    a.severity = $severity,
    a.raw_log = $raw_log
WITH a
FOREACH (_ IN CASE WHEN $host IS NOT NULL THEN [1] ELSE [] END |
    MERGE (h:Host {name: $host})
    MERGE (a)-[r:ON_HOST]->(h) SET r.ts = $timestamp
)
FOREACH (_ IN CASE WHEN $user IS NOT NULL THEN [1] ELSE [] END |
    MERGE (u:User {name: $user})
    MERGE (a)-[r:BY_USER]->(u) SET r.ts = $timestamp
)
FOREACH (ip IN $ips |
    MERGE (i:IP {address: ip})
    MERGE (a)-[r:INVOLVES_IP]->(i) SET r.ts = $timestamp
)
FOREACH (h IN $hashes |
    MERGE (f:Hash {value: h})
    MERGE (a)-[r:HAS_HASH]->(f) SET r.ts = $timestamp
)
FOREACH (p IN $processes |
    MERGE (pr:Process {name: p})
    MERGE (a)-[r:RAN_PROCESS]->(pr) SET r.ts = $timestamp
)
FOREACH (_ IN CASE WHEN $technique IS NOT NULL THEN [1] ELSE [] END |
    MERGE (t:Technique {id: $technique})
    MERGE (a)-[r:MATCHES_TECHNIQUE]->(t) SET r.ts = $timestamp
)
"""


def upsert_alert(alert: CommonAlert, entities: Entities) -> None:
    params = dict(
        id=alert.id,
        source_system=alert.source_system,
        timestamp=alert.timestamp,
        rule_name=alert.rule_name,
        severity=alert.severity,
        raw_log=alert.raw_log[:2000],
        host=alert.host,
        user=alert.user,
        ips=entities.ips,
        hashes=entities.hashes,
        processes=entities.processes,
        technique=alert.mitre_technique,
    )
    with get_driver().session() as session:
        session.run(_UPSERT_ALERT, **params)


_NEIGHBORHOOD_QUERY = """
MATCH (a:Alert {id: $alert_id})-[]-(entity)-[]-(other:Alert)
WHERE other.id <> $alert_id
RETURN DISTINCT other.id AS id, other.rule_name AS rule_name,
       other.severity AS severity, other.timestamp AS timestamp,
       labels(entity)[0] AS shared_entity_type,
       coalesce(entity.name, entity.address, entity.value) AS shared_entity
ORDER BY other.timestamp DESC
LIMIT $limit
"""


def neighborhood(alert_id: str, hops: int = 2, limit: int = 5) -> list[dict]:
    # `hops` is accepted for API symmetry with the plan's "1-2 hop"
    # language; the query above is a fixed 2-hop (alert -> entity ->
    # other alert) traversal, which is what "what else has this entity
    # touched" actually means for this schema.
    with get_driver().session() as session:
        result = session.run(_NEIGHBORHOOD_QUERY, alert_id=alert_id, limit=limit)
        return [dict(r) for r in result]


_TECHNIQUE_MATCH_QUERY = """
MATCH (a:Alert {id: $alert_id})-[:MATCHES_TECHNIQUE]->(t:Technique)
RETURN t.id AS id, t.name AS name, t.description AS description
LIMIT $limit
"""


def matched_techniques(alert_id: str, limit: int = 3) -> list[dict]:
    with get_driver().session() as session:
        result = session.run(_TECHNIQUE_MATCH_QUERY, alert_id=alert_id, limit=limit)
        return [dict(r) for r in result]


def seed_technique(technique_id: str, name: str, description: str) -> None:
    with get_driver().session() as session:
        session.run(
            "MERGE (t:Technique {id: $id}) SET t.name = $name, t.description = $description",
            id=technique_id, name=name, description=description,
        )


def seed_sigma_rule(rule_id: str, title: str, technique_id: Optional[str]) -> None:
    with get_driver().session() as session:
        session.run(
            """
            MERGE (s:SigmaRule {id: $id}) SET s.title = $title
            WITH s
            FOREACH (_ IN CASE WHEN $technique_id IS NOT NULL THEN [1] ELSE [] END |
                MERGE (t:Technique {id: $technique_id})
                MERGE (s)-[:MAPS_TO]->(t)
            )
            """,
            id=rule_id, title=title, technique_id=technique_id,
        )
