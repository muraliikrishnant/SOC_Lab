import hashlib
import time
from typing import Optional

from pydantic import BaseModel, Field


class CommonAlert(BaseModel):
    """Normalized alert shape every SIEM adapter converts its raw payload into.

    Everything downstream of the adapters (entity extraction, graph, vector
    store, LLM reasoning) reads this shape only and never touches a
    SIEM-specific field name again.
    """

    id: str
    source_system: str  # "splunk" | "elastic" | "wazuh"
    timestamp: float = Field(default_factory=time.time)
    host: Optional[str] = None
    user: Optional[str] = None
    src_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    process: Optional[str] = None
    hash: Optional[str] = None
    rule_name: Optional[str] = None
    severity: str = "unknown"  # low | medium | high | critical | unknown
    mitre_technique: Optional[str] = None
    raw_log: str = ""
    raw: dict = Field(default_factory=dict)

    @staticmethod
    def make_id(source_system: str, natural_key: str) -> str:
        digest = hashlib.sha256(f"{source_system}:{natural_key}".encode()).hexdigest()[:16]
        return f"{source_system}-{digest}"


class Entities(BaseModel):
    ips: list[str] = Field(default_factory=list)
    hashes: list[str] = Field(default_factory=list)
    cves: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)
    hosts: list[str] = Field(default_factory=list)
    processes: list[str] = Field(default_factory=list)


class RetrievalContext(BaseModel):
    related_alerts: list[dict] = Field(default_factory=list)
    matched_techniques: list[dict] = Field(default_factory=list)
    matched_sigma_rules: list[dict] = Field(default_factory=list)
    similar_past_alerts: list[dict] = Field(default_factory=list)


class Verdict(BaseModel):
    alert_id: str
    source_system: str
    timestamp: float = Field(default_factory=time.time)
    severity: str = "unknown"
    mitre_technique: Optional[str] = None
    confidence: float = 0.0
    cited_evidence: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    summary: str = ""
    host: Optional[str] = None
    user: Optional[str] = None
    src_ip: Optional[str] = None
    rule_name: Optional[str] = None
