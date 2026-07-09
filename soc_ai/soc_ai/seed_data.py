"""Load the curated MITRE ATT&CK technique subset and SigmaHQ-style rule
subset into both stores (Section 3.2/4 of the build plan — grounding
knowledge, loaded once at startup, no custom code needed for it to be
useful). This is a starter set (~30 techniques, ~15 rules) covering the
common SOC alert categories (brute force, persistence, discovery, C2,
exfil, ransomware) — swap in the full MITRE STIX/TAXII feed and the full
SigmaHQ repo later by pointing this same loader at more records.
"""
import json
import logging
import os

from . import graph, vectorstore

log = logging.getLogger(__name__)
_SEED_DIR = os.path.join(os.path.dirname(__file__), "seed")


def _load(name: str) -> list[dict]:
    with open(os.path.join(_SEED_DIR, name)) as f:
        return json.load(f)


def run() -> dict:
    graph.ensure_constraints()

    techniques = _load("attack_techniques.json")
    for t in techniques:
        graph.seed_technique(t["id"], t["name"], t["description"])
        vectorstore.upsert(
            f"technique-{t['id']}",
            f"{t['name']}: {t['description']}",
            {"type": "technique", "technique_id": t["id"], "name": t["name"], "description": t["description"]},
        )

    rules = _load("sigma_rules.json")
    for r in rules:
        graph.seed_sigma_rule(r["id"], r["title"], r.get("technique_id"))
        vectorstore.upsert(
            r["id"],
            f"{r['title']}: {r['description']}",
            {"type": "sigma", "title": r["title"], "description": r["description"], "technique_id": r.get("technique_id")},
        )

    log.info("Seeded %d techniques and %d Sigma rules", len(techniques), len(rules))
    return {"techniques": len(techniques), "sigma_rules": len(rules)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(run())
