"""
Threat Intelligence tools for the Guardian Agent.

Integrations:
  - AbuseIPDB (real API, requires ABUSEIPDB_API_KEY)
  - VirusTotal  (mock implementation — structure matches real VT API v3)

Both functions are wrapped as LangChain tools so they can be
called directly by LangGraph nodes.
"""

from __future__ import annotations
import os
import json
import hashlib
import random
import time
from typing import Any

import httpx
from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# AbuseIPDB  (real integration)
# ---------------------------------------------------------------------------

@tool
def check_ip_abuseipdb(ip_address: str) -> dict[str, Any]:
    """
    Query AbuseIPDB for the reputation of an IP address.
    Returns abuse confidence score, country, ISP, and recent reports.
    Falls back to a mock response if no API key is configured.
    """
    api_key = os.getenv("ABUSEIPDB_API_KEY", "")

    if not api_key:
        return _mock_abuseipdb_response(ip_address)

    url = "https://api.abuseipdb.com/api/v2/check"
    headers = {
        "Key": api_key,
        "Accept": "application/json",
    }
    params = {
        "ipAddress": ip_address,
        "maxAgeInDays": 90,
        "verbose": True,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json().get("data", {})
            return {
                "source": "AbuseIPDB",
                "indicator": ip_address,
                "indicator_type": "ip",
                "abuse_confidence_score": data.get("abuseConfidenceScore", 0),
                "country_code": data.get("countryCode", "XX"),
                "usage_type": data.get("usageType", "Unknown"),
                "isp": data.get("isp", "Unknown"),
                "domain": data.get("domain", ""),
                "total_reports": data.get("totalReports", 0),
                "last_reported_at": data.get("lastReportedAt", ""),
                "is_whitelisted": data.get("isWhitelisted", False),
                "is_malicious": data.get("abuseConfidenceScore", 0) > 25,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "source": "AbuseIPDB",
            "indicator": ip_address,
            "error": str(exc),
            "is_malicious": False,
        }


def _mock_abuseipdb_response(ip_address: str) -> dict[str, Any]:
    """Deterministic mock based on IP hash so results are reproducible in tests."""
    seed = int(hashlib.md5(ip_address.encode()).hexdigest()[:8], 16)  # noqa: S324
    rng = random.Random(seed)

    # A handful of "known bad" IPs for demo purposes
    known_bad = {
        "185.220.101.47": 98,
        "194.165.16.11": 87,
        "45.142.212.100": 76,
        "103.21.244.0": 65,
    }

    score = known_bad.get(ip_address, rng.randint(0, 30))
    country = rng.choice(["RU", "CN", "US", "DE", "NL", "UA", "BR"])
    isp = rng.choice([
        "Frantech Solutions", "Mullvad VPN", "Hetzner Online GmbH",
        "DigitalOcean LLC", "Amazon Technologies", "Unknown Hosting",
    ])

    return {
        "source": "AbuseIPDB (mock)",
        "indicator": ip_address,
        "indicator_type": "ip",
        "abuse_confidence_score": score,
        "country_code": country,
        "usage_type": "Data Center/Web Hosting/Transit",
        "isp": isp,
        "domain": "",
        "total_reports": rng.randint(0, 500) if score > 25 else rng.randint(0, 5),
        "last_reported_at": "2024-11-15T08:22:33+00:00" if score > 25 else "",
        "is_whitelisted": False,
        "is_malicious": score > 25,
    }


# ---------------------------------------------------------------------------
# VirusTotal  (mock — mirrors real VT API v3 schema)
# ---------------------------------------------------------------------------

@tool
def check_hash_virustotal(file_hash: str) -> dict[str, Any]:
    """
    Query VirusTotal for information about a file hash (MD5, SHA1, or SHA256).
    Uses the real VT API if VT_API_KEY is set, otherwise returns a realistic mock.
    """
    api_key = os.getenv("VIRUSTOTAL_API_KEY", "") or os.getenv("VT_API_KEY", "")

    if not api_key:
        return _mock_virustotal_response(file_hash)

    url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
    headers = {"x-apikey": api_key}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 404:
                return {
                    "source": "VirusTotal",
                    "indicator": file_hash,
                    "indicator_type": "hash",
                    "found": False,
                    "is_malicious": False,
                    "message": "Hash not found in VirusTotal database.",
                }
            response.raise_for_status()
            attrs = response.json().get("data", {}).get("attributes", {})
            stats = attrs.get("last_analysis_stats", {})
            malicious_count = stats.get("malicious", 0)
            total_engines = sum(stats.values())
            return {
                "source": "VirusTotal",
                "indicator": file_hash,
                "indicator_type": "hash",
                "found": True,
                "malicious_count": malicious_count,
                "total_engines": total_engines,
                "detection_ratio": f"{malicious_count}/{total_engines}",
                "meaningful_name": attrs.get("meaningful_name", ""),
                "type_description": attrs.get("type_description", ""),
                "tags": attrs.get("tags", []),
                "popular_threat_name": (
                    attrs.get("popular_threat_classification", {})
                    .get("suggested_threat_label", "")
                ),
                "is_malicious": malicious_count > 5,
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "source": "VirusTotal",
            "indicator": file_hash,
            "error": str(exc),
            "is_malicious": False,
        }


@tool
def check_url_virustotal(url: str) -> dict[str, Any]:
    """
    Query VirusTotal for information about a URL or domain.
    Uses the real VT API if VIRUSTOTAL_API_KEY is set.
    """
    import base64
    api_key = os.getenv("VIRUSTOTAL_API_KEY", "") or os.getenv("VT_API_KEY", "")

    if not api_key:
        return {
            "source": "VirusTotal (mock)",
            "indicator": url,
            "indicator_type": "url",
            "is_malicious": "payload" in url.lower() or "malware" in url.lower(),
            "message": "No API key configured.",
        }

    # VT API requires base64url encoding of the URL
    url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
    endpoint = f"https://www.virustotal.com/api/v3/urls/{url_id}"
    headers = {"x-apikey": api_key}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(endpoint, headers=headers)
            if response.status_code == 404:
                # Submit URL for scanning first
                scan_resp = client.post(
                    "https://www.virustotal.com/api/v3/urls",
                    headers=headers,
                    data={"url": url},
                )
                return {
                    "source": "VirusTotal",
                    "indicator": url,
                    "indicator_type": "url",
                    "found": False,
                    "is_malicious": False,
                    "message": "URL submitted for scanning. Check back later.",
                }
            response.raise_for_status()
            attrs = response.json().get("data", {}).get("attributes", {})
            stats = attrs.get("last_analysis_stats", {})
            malicious_count = stats.get("malicious", 0)
            total_engines = sum(stats.values())
            return {
                "source": "VirusTotal",
                "indicator": url,
                "indicator_type": "url",
                "found": True,
                "malicious_count": malicious_count,
                "total_engines": total_engines,
                "detection_ratio": f"{malicious_count}/{total_engines}",
                "is_malicious": malicious_count > 3,
                "categories": attrs.get("categories", {}),
                "last_analysis_date": attrs.get("last_analysis_date", ""),
            }
    except Exception as exc:
        return {
            "source": "VirusTotal",
            "indicator": url,
            "error": str(exc),
            "is_malicious": False,
        }



    """Deterministic mock based on hash value."""
    seed = int(hashlib.md5(file_hash.encode()).hexdigest()[:8], 16)  # noqa: S324
    rng = random.Random(seed)

    # Known-bad hashes for demo
    known_bad_hashes = {
        "44d88612fea8a8f36de82e1278abb02f": ("Mirai.Botnet", 58, 72),
        "e3b0c44298fc1c149afbf4c8996fb924": ("Clean file", 0, 72),
        "3395856ce81f2b7382dee72602f798b6": ("Emotet.Dropper", 61, 72),
        "abc123def456abc123def456abc123de": ("Cobalt.Strike.Beacon", 55, 72),
    }

    if file_hash in known_bad_hashes:
        name, mal_count, total = known_bad_hashes[file_hash]
        is_malicious = mal_count > 5
    else:
        mal_count = rng.choice([0, 0, 0, rng.randint(1, 65)])
        total = 72
        name = rng.choice(["", "", "Suspicious.GenericKD", "Backdoor.Generic"])
        is_malicious = mal_count > 5

    return {
        "source": "VirusTotal (mock)",
        "indicator": file_hash,
        "indicator_type": "hash",
        "found": True,
        "malicious_count": mal_count,
        "total_engines": total,
        "detection_ratio": f"{mal_count}/{total}",
        "meaningful_name": name,
        "type_description": "Win32 EXE" if is_malicious else "Unknown",
        "tags": ["peexe", "overlay"] if is_malicious else [],
        "popular_threat_name": name if is_malicious else "",
        "is_malicious": is_malicious,
    }


# ---------------------------------------------------------------------------
# Convenience wrapper: run all relevant checks for a list of indicators
# ---------------------------------------------------------------------------

def bulk_investigate(indicators: list[str]) -> list[dict[str, Any]]:
    """
    Given a mixed list of indicators, route each one to the appropriate tool:
    - IP addresses → AbuseIPDB
    - File hashes (MD5/SHA1/SHA256) → VirusTotal
    - URLs / domains → VirusTotal URL check
    """
    results = []
    for indicator in indicators:
        stripped = indicator.strip()
        if _looks_like_hash(stripped):
            result = check_hash_virustotal.invoke({"file_hash": stripped})
            print(f"  🔬 [VT HASH] {stripped[:16]}... → {result.get('detection_ratio', '?')} engines")
        elif _looks_like_ip(stripped):
            result = check_ip_abuseipdb.invoke({"ip_address": stripped})
        elif _looks_like_url(stripped):
            result = check_url_virustotal.invoke({"url": stripped})
            print(f"  🔬 [VT URL] {stripped[:40]} → malicious={result.get('is_malicious')}")
        else:
            result = {
                "source": "Guardian",
                "indicator": stripped,
                "indicator_type": "identifier",
                "is_malicious": False,
                "message": "Unknown indicator type — manual review recommended.",
            }
        results.append(result)
        time.sleep(0.25)  # VT free tier: 4 req/min

    return results


def _looks_like_hash(value: str) -> bool:
    hex_chars = set("0123456789abcdefABCDEF")
    return len(value) in (32, 40, 64) and all(c in hex_chars for c in value)


def _looks_like_ip(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(p) <= 255 for p in parts)
    except ValueError:
        return False


def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://", "ftp://")) or (
        "." in value and "/" in value and not _looks_like_ip(value.split("/")[0])
    )