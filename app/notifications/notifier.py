"""
Guardian Notifier — Email (SMTP) + Slack (webhook)

Configure via .env:
  EMAIL_ENABLED=true
  EMAIL_FROM=guardian@yourcompany.com
  EMAIL_TO=soc-team@yourcompany.com
  EMAIL_SMTP_HOST=smtp.gmail.com
  EMAIL_SMTP_PORT=587
  EMAIL_SMTP_USER=youruser@gmail.com
  EMAIL_SMTP_PASS=your_app_password

  SLACK_ENABLED=true
  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ

Usage:
  from app.notifications.notifier import notify_incident_created, notify_incident_complete
  notify_incident_created(incident)
  notify_incident_complete(incident)
"""

from __future__ import annotations
import os
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Any

import httpx


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _risk_label(score: int) -> str:
    if score >= 9: return "🔴 CRITICAL"
    if score >= 7: return "🟠 HIGH"
    if score >= 4: return "🟡 MEDIUM"
    return "🟢 LOW"


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

def _send_slack(message: dict[str, Any]) -> bool:
    webhook = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook:
        return False
    try:
        resp = httpx.post(webhook, json=message, timeout=10)
        resp.raise_for_status()
        print(f"  📨 [SLACK] Notification sent")
        return True
    except Exception as e:
        print(f"  ⚠️  [SLACK] Failed: {e}")
        return False


def _slack_incident_created(incident: dict[str, Any]) -> None:
    risk = incident.get("risk_score", 0)
    iid = incident.get("id") or incident.get("incident_id", "?")
    indicators = incident.get("found_indicators", [])

    _send_slack({
        "text": f"*⚠️ New Guardian Incident* — {_risk_label(risk)}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"⚠️ New Incident Detected — Risk {risk}/10"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident ID:*\n`{iid[:8].upper()}`"},
                    {"type": "mrkdwn", "text": f"*Risk Score:*\n{_risk_label(risk)} ({risk}/10)"},
                    {"type": "mrkdwn", "text": f"*Source:*\n{incident.get('log_source', 'unknown')}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{_now()}"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Indicators:*\n{', '.join(indicators) if indicators else 'None yet'}"}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔍 View Incident"},
                        "url": f"{os.getenv('DASHBOARD_URL', 'http://localhost:3000')}",
                        "style": "danger" if risk >= 7 else "primary"
                    }
                ]
            }
        ]
    })


def _slack_incident_complete(incident: dict[str, Any]) -> None:
    risk = incident.get("risk_score", 0)
    iid = incident.get("id") or incident.get("incident_id", "?")
    actions = incident.get("executed_actions", [])

    _send_slack({
        "text": f"*✅ Guardian Incident Complete* — {_risk_label(risk)}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"✅ Incident Resolved — {len(actions)} Actions Taken"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Incident ID:*\n`{iid[:8].upper()}`"},
                    {"type": "mrkdwn", "text": f"*Risk Score:*\n{_risk_label(risk)} ({risk}/10)"},
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*Actions Executed:*\n" + "\n".join(f"• {a}" for a in actions) if actions else "No actions taken"}
            }
        ]
    })


def _slack_approval_needed(incident: dict[str, Any]) -> None:
    risk = incident.get("risk_score", 0)
    iid = incident.get("id") or incident.get("incident_id", "?")
    plan = (incident.get("mitigation_plan") or "").split("__ACTIONS__")[0][:300]

    _send_slack({
        "text": f"🚨 *APPROVAL REQUIRED* — Risk {risk}/10 incident needs authorization",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 Human Approval Required"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Incident `{iid[:8].upper()}` has risk score *{risk}/10* and requires manual authorization before executing mitigation actions."}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Proposed Plan:*\n{plan}..."}
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Review & Approve"},
                        "url": f"{os.getenv('DASHBOARD_URL', 'http://localhost:3000')}",
                        "style": "danger"
                    }
                ]
            }
        ]
    })


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def _send_email(subject: str, html_body: str) -> bool:
    if os.getenv("EMAIL_ENABLED", "").lower() not in ("true", "1"):
        return False

    smtp_host = os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    smtp_user = os.getenv("EMAIL_SMTP_USER", "")
    smtp_pass = os.getenv("EMAIL_SMTP_PASS", "")
    email_from = os.getenv("EMAIL_FROM", smtp_user)
    email_to = os.getenv("EMAIL_TO", "")

    if not all([smtp_user, smtp_pass, email_to]):
        print("  ⚠️  [EMAIL] Missing config — set EMAIL_SMTP_USER, EMAIL_SMTP_PASS, EMAIL_TO")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = email_from
        msg["To"] = email_to
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(email_from, email_to.split(","), msg.as_string())

        print(f"  📧 [EMAIL] Sent to {email_to}")
        return True
    except Exception as e:
        print(f"  ⚠️  [EMAIL] Failed: {e}")
        return False


def _email_incident_created(incident: dict[str, Any]) -> None:
    risk = incident.get("risk_score", 0)
    iid = incident.get("id") or incident.get("incident_id", "?")
    indicators = incident.get("found_indicators", [])
    color = "#ff3355" if risk >= 9 else "#ff8c00" if risk >= 7 else "#ffd700" if risk >= 4 else "#00ff88"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0f1e; color: #e0eeff; padding: 24px; border-radius: 8px;">
        <div style="background: {color}22; border: 1px solid {color}44; border-radius: 6px; padding: 20px; margin-bottom: 20px;">
            <h1 style="color: {color}; margin: 0 0 8px 0; font-size: 20px;">⚠️ New Guardian Incident</h1>
            <p style="color: #7090b0; margin: 0;">Detected at {_now()}</p>
        </div>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #1a2845; color: #7090b0; width: 40%;">Incident ID</td>
                <td style="padding: 10px; border-bottom: 1px solid #1a2845; font-family: monospace; color: #00d4ff;">{iid[:8].upper()}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #1a2845; color: #7090b0;">Risk Score</td>
                <td style="padding: 10px; border-bottom: 1px solid #1a2845; color: {color}; font-weight: bold;">{risk}/10 — {_risk_label(risk)}</td>
            </tr>
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #1a2845; color: #7090b0;">Source</td>
                <td style="padding: 10px; border-bottom: 1px solid #1a2845;">{incident.get('log_source', 'unknown')}</td>
            </tr>
            <tr>
                <td style="padding: 10px; color: #7090b0;">Indicators</td>
                <td style="padding: 10px; font-family: monospace; font-size: 13px;">{', '.join(indicators) if indicators else 'Analyzing...'}</td>
            </tr>
        </table>
        <div style="margin-top: 24px; text-align: center;">
            <a href="{os.getenv('DASHBOARD_URL', 'http://localhost:3000')}" style="background: {color}22; color: {color}; border: 1px solid {color}44; padding: 12px 24px; border-radius: 4px; text-decoration: none; font-weight: bold;">
                View in Guardian Dashboard →
            </a>
        </div>
    </div>
    """
    _send_email(f"[Guardian] New Incident — Risk {risk}/10 ({_risk_label(risk)})", html)


def _email_approval_needed(incident: dict[str, Any]) -> None:
    risk = incident.get("risk_score", 0)
    iid = incident.get("id") or incident.get("incident_id", "?")

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #0a0f1e; color: #e0eeff; padding: 24px; border-radius: 8px;">
        <div style="background: #ff8c0022; border: 2px solid #ff8c0066; border-radius: 6px; padding: 20px; margin-bottom: 20px;">
            <h1 style="color: #ff8c00; margin: 0 0 8px 0; font-size: 20px;">🚨 Approval Required</h1>
            <p style="color: #7090b0; margin: 0;">Incident {iid[:8].upper()} requires your authorization</p>
        </div>
        <p style="color: #e0eeff; line-height: 1.6;">
            Guardian has detected a <strong style="color: #ff8c00;">Risk {risk}/10</strong> threat and has prepared mitigation actions.
            These actions require your manual approval before execution.
        </p>
        <div style="margin-top: 24px; text-align: center;">
            <a href="{os.getenv('DASHBOARD_URL', 'http://localhost:3000')}" style="background: #ff8c0022; color: #ff8c00; border: 1px solid #ff8c0044; padding: 14px 32px; border-radius: 4px; text-decoration: none; font-weight: bold; font-size: 16px;">
                ✅ Review &amp; Approve Actions →
            </a>
        </div>
    </div>
    """
    _send_email(f"[Guardian] 🚨 APPROVAL REQUIRED — Incident {iid[:8].upper()} Risk {risk}/10", html)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def notify_incident_created(incident: dict[str, Any]) -> None:
    """Call when a new incident is created."""
    if os.getenv("SLACK_ENABLED", "").lower() in ("true", "1"):
        _slack_incident_created(incident)
    if os.getenv("EMAIL_ENABLED", "").lower() in ("true", "1"):
        _email_incident_created(incident)


def notify_approval_needed(incident: dict[str, Any]) -> None:
    """Call when HITL approval is needed (risk > 7)."""
    if os.getenv("SLACK_ENABLED", "").lower() in ("true", "1"):
        _slack_approval_needed(incident)
    if os.getenv("EMAIL_ENABLED", "").lower() in ("true", "1"):
        _email_approval_needed(incident)


def notify_incident_complete(incident: dict[str, Any]) -> None:
    """Call when an incident completes."""
    if os.getenv("SLACK_ENABLED", "").lower() in ("true", "1"):
        _slack_incident_complete(incident)