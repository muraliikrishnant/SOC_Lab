"""Report generation, split into a free templating layer and a single
batched LLM call for narrative — see project notes on why report writing
shouldn't cost one inference call per field.
"""
import datetime
import os
from collections import Counter
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .reasoning import generate_digest_narrative
from .schema import Verdict

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=select_autoescape(disabled_extensions=("j2",)))


def _with_timestamp_str(verdict: Verdict) -> dict:
    d = verdict.model_dump()
    d["timestamp_str"] = datetime.datetime.fromtimestamp(verdict.timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return d


def render_alert_report(verdict: Verdict) -> str:
    template = _env.get_template("alert_report.md.j2")
    return template.render(verdict=_with_timestamp_str(verdict))


def render_digest_report(verdicts: list[Verdict], narrative: Optional[str] = None) -> str:
    template = _env.get_template("digest_report.md.j2")
    counts = Counter(v.severity if v.severity in ("low", "medium", "high", "critical") else "unknown" for v in verdicts)
    return template.render(
        generated_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        verdicts=verdicts,
        severity_counts={k: counts.get(k, 0) for k in ("critical", "high", "medium", "low", "unknown")},
        narrative=narrative if narrative is not None else generate_digest_narrative(verdicts),
    )
