"""Lightweight verdict persistence for the digest report — appends to a
JSONL file rather than standing up a fourth database, since the only
query this needs to serve is "verdicts since time T"."""
import json
import os
import time

from . import config
from .schema import Verdict

_PATH = os.path.join(config.DATA_DIR, "verdicts.jsonl")


def append(verdict: Verdict) -> None:
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    with open(_PATH, "a") as f:
        f.write(json.dumps(verdict.model_dump()) + "\n")


def recent(since_seconds: float = 12 * 3600) -> list[Verdict]:
    if not os.path.exists(_PATH):
        return []
    cutoff = time.time() - since_seconds
    verdicts = []
    with open(_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("timestamp", 0) >= cutoff:
                verdicts.append(Verdict(**d))
    return verdicts
