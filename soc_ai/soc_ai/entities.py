import re

from .schema import CommonAlert, Entities

# Deterministic regex extraction. This is intentionally not an LLM call:
# IPs/hashes/CVEs are structured tokens with a fixed shape, and regex is
# faster and more reliable than spending inference on something a pattern
# already answers.

_IPV4_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b")
_MD5_RE = re.compile(r"\b[a-fA-F0-9]{32}\b")
_SHA1_RE = re.compile(r"\b[a-fA-F0-9]{40}\b")
_SHA256_RE = re.compile(r"\b[a-fA-F0-9]{64}\b")
_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)

# Private/reserved ranges we don't bother treating as attacker-controlled IOCs
_IGNORED_IP_PREFIXES = ("0.", "127.", "255.255.255.255")


def _is_routable(ip: str) -> bool:
    return not ip.startswith(_IGNORED_IP_PREFIXES)


def extract_entities(alert: CommonAlert) -> Entities:
    text = " ".join(
        str(v) for v in (alert.raw_log, alert.rule_name, alert.process, alert.hash) if v
    )

    ips = {m for m in _IPV4_RE.findall(text) if _is_routable(m)}
    if alert.src_ip:
        ips.add(alert.src_ip)
    if alert.dest_ip:
        ips.add(alert.dest_ip)

    hashes = set(_SHA256_RE.findall(text)) | set(_SHA1_RE.findall(text)) | set(_MD5_RE.findall(text))
    if alert.hash:
        hashes.add(alert.hash)

    cves = {m.upper() for m in _CVE_RE.findall(text)}

    users = {alert.user} if alert.user else set()
    hosts = {alert.host} if alert.host else set()
    processes = {alert.process} if alert.process else set()

    return Entities(
        ips=sorted(ips),
        hashes=sorted(hashes),
        cves=sorted(cves),
        users=sorted(users),
        hosts=sorted(hosts),
        processes=sorted(processes),
    )
