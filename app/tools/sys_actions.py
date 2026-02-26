"""
System action tools for the Guardian Agent — v2.

Includes:
  - block_ip_firewall        : JSON firewall rules (mock)
  - block_file_hash          : JSON endpoint blocklist (mock)
  - disable_user_account     : Okta OR Azure AD (real APIs) with JSON fallback
  - isolate_host             : JSON quarantine registry (mock)
  - send_alert               : JSON alert log (mock / webhook)
"""

from __future__ import annotations
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from langchain_core.tools import tool


_STATE_DIR = Path(os.getenv("GUARDIAN_STATE_DIR", "/tmp"))


def _load_store(filename: str) -> dict[str, Any]:
    path = _STATE_DIR / filename
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def _save_store(filename: str, data: dict[str, Any]) -> None:
    (_STATE_DIR / filename).write_text(json.dumps(data, indent=2))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Firewall
# ---------------------------------------------------------------------------

@tool
def block_ip_firewall(ip_address: str, reason: str = "Threat detected by Guardian") -> dict[str, Any]:
    """Block an IP address in the Guardian firewall deny-list."""
    store = _load_store("guardian_firewall.json")
    rules = store.get("deny_rules", [])
    existing = next((r for r in rules if r["ip"] == ip_address), None)
    if existing:
        return {"action": "block_ip", "status": "already_blocked", "ip": ip_address, "blocked_at": existing["blocked_at"]}
    rule = {"ip": ip_address, "reason": reason, "blocked_at": _now(), "blocked_by": "guardian_agent"}
    rules.append(rule)
    store["deny_rules"] = rules
    _save_store("guardian_firewall.json", store)
    print(f"  🔥 [FIREWALL] Blocked IP: {ip_address}")
    return {"action": "block_ip", "status": "success", "ip": ip_address, "blocked_at": rule["blocked_at"]}


# ---------------------------------------------------------------------------
# Hash blocklist
# ---------------------------------------------------------------------------

@tool
def block_file_hash(file_hash: str, threat_name: str = "Unknown malware") -> dict[str, Any]:
    """Add a file hash to the endpoint security blocklist."""
    store = _load_store("guardian_blocklist.json")
    hashes = store.get("blocked_hashes", [])
    existing = next((h for h in hashes if h["hash"] == file_hash), None)
    if existing:
        return {"action": "block_hash", "status": "already_blocked", "hash": file_hash}
    entry = {"hash": file_hash, "threat_name": threat_name, "blocked_at": _now(), "blocked_by": "guardian_agent"}
    hashes.append(entry)
    store["blocked_hashes"] = hashes
    _save_store("guardian_blocklist.json", store)
    print(f"  🚫 [BLOCKLIST] Blocked hash: {file_hash[:16]}...")
    return {"action": "block_hash", "status": "success", "hash": file_hash, "blocked_at": entry["blocked_at"]}


# ---------------------------------------------------------------------------
# User disable — Okta / Azure AD / JSON fallback
# ---------------------------------------------------------------------------

def _disable_user_okta(username: str, reason: str) -> dict[str, Any]:
    """Suspend a user in Okta via the Users API."""
    okta_domain = os.getenv("OKTA_DOMAIN", "")
    okta_token = os.getenv("OKTA_API_TOKEN", "")

    if not okta_domain or not okta_token:
        return {}

    headers = {
        "Authorization": f"SSWS {okta_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            # Find user by login/email
            search_resp = client.get(
                f"https://{okta_domain}/api/v1/users",
                headers=headers,
                params={"search": f'profile.login eq "{username}" or profile.email eq "{username}"'},
            )
            search_resp.raise_for_status()
            users = search_resp.json()
            if not users:
                return {"action": "disable_user", "status": "not_found", "username": username, "provider": "okta"}

            user_id = users[0]["id"]
            current_status = users[0].get("status", "UNKNOWN")

            if current_status == "SUSPENDED":
                return {"action": "disable_user", "status": "already_disabled", "username": username, "provider": "okta"}

            # Suspend the user
            suspend_resp = client.post(
                f"https://{okta_domain}/api/v1/users/{user_id}/lifecycle/suspend",
                headers=headers,
            )
            suspend_resp.raise_for_status()

            print(f"  🔒 [OKTA] Suspended user: {username} (id={user_id})")
            return {
                "action": "disable_user",
                "status": "success",
                "username": username,
                "user_id": user_id,
                "provider": "okta",
                "disabled_at": _now(),
                "reason": reason,
            }
    except Exception as exc:
        return {"action": "disable_user", "status": "error", "username": username, "provider": "okta", "error": str(exc)}


def _disable_user_azure_ad(username: str, reason: str) -> dict[str, Any]:
    """Disable a user in Azure AD via Microsoft Graph API."""
    tenant_id = os.getenv("AZURE_TENANT_ID", "")
    client_id = os.getenv("AZURE_CLIENT_ID", "")
    client_secret = os.getenv("AZURE_CLIENT_SECRET", "")

    if not all([tenant_id, client_id, client_secret]):
        return {}

    try:
        with httpx.Client(timeout=15.0) as client:
            # Get access token
            token_resp = client.post(
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Find user
            search_resp = client.get(
                f"https://graph.microsoft.com/v1.0/users",
                headers=headers,
                params={"$filter": f"userPrincipalName eq '{username}' or mail eq '{username}'"},
            )
            search_resp.raise_for_status()
            users = search_resp.json().get("value", [])
            if not users:
                return {"action": "disable_user", "status": "not_found", "username": username, "provider": "azure_ad"}

            user_id = users[0]["id"]

            # Disable account
            patch_resp = client.patch(
                f"https://graph.microsoft.com/v1.0/users/{user_id}",
                headers=headers,
                json={"accountEnabled": False},
            )
            patch_resp.raise_for_status()

            print(f"  🔒 [AZURE AD] Disabled user: {username} (id={user_id})")
            return {
                "action": "disable_user",
                "status": "success",
                "username": username,
                "user_id": user_id,
                "provider": "azure_ad",
                "disabled_at": _now(),
                "reason": reason,
            }
    except Exception as exc:
        return {"action": "disable_user", "status": "error", "username": username, "provider": "azure_ad", "error": str(exc)}


def _disable_user_local(username: str, reason: str) -> dict[str, Any]:
    """Fallback: persist disable to local JSON store."""
    store = _load_store("guardian_directory.json")
    users = store.get("users", {})
    users[username] = {
        "status": "DISABLED",
        "reason": reason,
        "disabled_at": _now(),
        "disabled_by": "guardian_agent",
        "previous_status": users.get(username, {}).get("status", "ACTIVE"),
        "provider": "local_mock",
    }
    store["users"] = users
    _save_store("guardian_directory.json", store)
    print(f"  🔒 [DIRECTORY] Disabled user: {username} (local mock)")
    return {"action": "disable_user", "status": "success", "username": username, "provider": "local_mock", "disabled_at": users[username]["disabled_at"]}


@tool
def disable_user_account(username: str, reason: str = "Suspicious activity detected") -> dict[str, Any]:
    """
    Disable a user account. Tries Okta first, then Azure AD, then falls back to local JSON.
    Configure via OKTA_DOMAIN+OKTA_API_TOKEN or AZURE_TENANT_ID+AZURE_CLIENT_ID+AZURE_CLIENT_SECRET.
    """
    # Try Okta
    result = _disable_user_okta(username, reason)
    if result:
        return result

    # Try Azure AD
    result = _disable_user_azure_ad(username, reason)
    if result:
        return result

    # Fallback to local mock
    return _disable_user_local(username, reason)


# ---------------------------------------------------------------------------
# Host isolation
# ---------------------------------------------------------------------------

@tool
def isolate_host(hostname: str, reason: str = "Potential compromise") -> dict[str, Any]:
    """Mark a host for network isolation (quarantine VLAN)."""
    store = _load_store("guardian_isolation.json")
    hosts = store.get("isolated_hosts", [])
    existing = next((h for h in hosts if h["hostname"] == hostname), None)
    if existing:
        return {"action": "isolate_host", "status": "already_isolated", "hostname": hostname}
    entry = {"hostname": hostname, "reason": reason, "isolated_at": _now(), "isolated_by": "guardian_agent", "vlan": "QUARANTINE-999"}
    hosts.append(entry)
    store["isolated_hosts"] = hosts
    _save_store("guardian_isolation.json", store)
    print(f"  🏥 [ISOLATION] Isolated host: {hostname} → QUARANTINE VLAN")
    return {"action": "isolate_host", "status": "success", "hostname": hostname, "vlan_assigned": "QUARANTINE-999", "isolated_at": entry["isolated_at"]}


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------

@tool
def send_alert(severity: str, title: str, description: str, indicators: list[str] | None = None) -> dict[str, Any]:
    """Send a security alert to the SIEM / notification channel."""
    store = _load_store("guardian_alerts.json")
    alerts = store.get("alerts", [])
    alert = {
        "id": f"ALT-{int(time.time())}",
        "severity": severity.upper(),
        "title": title,
        "description": description,
        "indicators": indicators or [],
        "created_at": _now(),
        "created_by": "guardian_agent",
        "status": "OPEN",
    }
    alerts.append(alert)
    store["alerts"] = alerts
    _save_store("guardian_alerts.json", store)
    print(f"  📢 [ALERT] [{severity.upper()}] {title}")
    return {"action": "send_alert", "status": "success", "alert_id": alert["id"], "severity": severity}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

ACTION_TOOLS = {
    "block_ip": block_ip_firewall,
    "block_hash": block_file_hash,
    "disable_user": disable_user_account,
    "isolate_host": isolate_host,
    "alert_only": send_alert,
}


def execute_action(action_type: str, **kwargs: Any) -> dict[str, Any]:
    tool_fn = ACTION_TOOLS.get(action_type)
    if not tool_fn:
        return {"action": action_type, "status": "error", "message": f"Unknown action type: {action_type}"}
    return tool_fn.invoke(kwargs)


def get_current_state() -> dict[str, Any]:
    return {
        "firewall": _load_store("guardian_firewall.json"),
        "blocklist": _load_store("guardian_blocklist.json"),
        "directory": _load_store("guardian_directory.json"),
        "isolation": _load_store("guardian_isolation.json"),
        "alerts": _load_store("guardian_alerts.json"),
    }