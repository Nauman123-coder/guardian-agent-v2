"""
Guardian PDF Report Generator

Generates a professional incident report PDF using reportlab.

Usage:
    from app.reports.generator import generate_incident_pdf
    pdf_bytes = generate_incident_pdf(incident_dict)

Install:
    pip install reportlab
"""

from __future__ import annotations
import io
import os
from datetime import datetime, timezone
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import PageBreak


# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
BG_DARK    = colors.HexColor("#050810")
CYAN       = colors.HexColor("#00d4ff")
GREEN      = colors.HexColor("#00ff88")
RED        = colors.HexColor("#ff3355")
ORANGE     = colors.HexColor("#ff8c00")
YELLOW     = colors.HexColor("#ffd700")
PURPLE     = colors.HexColor("#8b5cf6")
TEXT_MAIN  = colors.HexColor("#e0eeff")
TEXT_DIM   = colors.HexColor("#7090b0")
BORDER     = colors.HexColor("#1a2845")
PANEL      = colors.HexColor("#0d1526")
WHITE      = colors.white
BLACK      = colors.black


def _risk_color(score: int):
    if score >= 9: return RED
    if score >= 7: return ORANGE
    if score >= 4: return YELLOW
    return GREEN


def _risk_label(score: int) -> str:
    if score >= 9: return "CRITICAL"
    if score >= 7: return "HIGH"
    if score >= 4: return "MEDIUM"
    return "LOW"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "GuardianTitle",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=CYAN,
            spaceAfter=4,
            alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "GuardianSubtitle",
            fontName="Helvetica",
            fontSize=10,
            textColor=TEXT_DIM,
            spaceAfter=16,
        ),
        "section": ParagraphStyle(
            "GuardianSection",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=CYAN,
            spaceBefore=16,
            spaceAfter=8,
            borderPad=4,
        ),
        "body": ParagraphStyle(
            "GuardianBody",
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_MAIN,
            leading=14,
            spaceAfter=6,
        ),
        "mono": ParagraphStyle(
            "GuardianMono",
            fontName="Courier",
            fontSize=8,
            textColor=TEXT_MAIN,
            leading=12,
            backColor=PANEL,
            borderPad=8,
        ),
        "label": ParagraphStyle(
            "GuardianLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=TEXT_DIM,
        ),
        "value": ParagraphStyle(
            "GuardianValue",
            fontName="Helvetica",
            fontSize=9,
            textColor=TEXT_MAIN,
        ),
    }
    return styles


# ---------------------------------------------------------------------------
# Page template (header/footer on every page)
# ---------------------------------------------------------------------------

def _add_page_decorations(canvas, doc):
    canvas.saveState()
    w, h = A4

    # Top bar
    canvas.setFillColor(PANEL)
    canvas.rect(0, h - 1.2*cm, w, 1.2*cm, fill=1, stroke=0)

    # Top bar accent line
    canvas.setFillColor(CYAN)
    canvas.rect(0, h - 1.2*cm, w, 2, fill=1, stroke=0)

    # Logo text
    canvas.setFillColor(CYAN)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(1.5*cm, h - 0.85*cm, "GUARDIAN AGENT")
    canvas.setFillColor(TEXT_DIM)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.5*cm, h - 1.05*cm, "Autonomous Threat Hunter & Incident Responder")

    # Page number top right
    canvas.setFillColor(TEXT_DIM)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 1.5*cm, h - 0.75*cm, f"Page {doc.page}")

    # Bottom bar
    canvas.setFillColor(PANEL)
    canvas.rect(0, 0, w, 0.9*cm, fill=1, stroke=0)
    canvas.setFillColor(BORDER)
    canvas.rect(0, 0.9*cm, w, 1, fill=1, stroke=0)
    canvas.setFillColor(TEXT_DIM)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(1.5*cm, 0.3*cm, f"Generated: {_now()}")
    canvas.drawRightString(w - 1.5*cm, 0.3*cm, "CONFIDENTIAL — FOR AUTHORIZED USE ONLY")

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_incident_pdf(incident: dict[str, Any]) -> bytes:
    """Generate a PDF report for an incident. Returns raw bytes."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.8*cm,
        bottomMargin=1.5*cm,
    )

    S = _build_styles()
    story = []
    w = A4[0] - 3*cm  # usable width

    iid = incident.get("id") or incident.get("incident_id", "UNKNOWN")
    risk = incident.get("risk_score", 0)
    risk_color = _risk_color(risk)
    status = incident.get("status", "unknown").upper()
    indicators = incident.get("found_indicators", [])
    ti_results = incident.get("investigation_results", [])
    actions = incident.get("executed_actions", [])
    plan_text = (incident.get("mitigation_plan") or "").split("__ACTIONS__")[0].strip()

    # ---- Title block -------------------------------------------------------
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("INCIDENT REPORT", S["title"]))
    story.append(Paragraph(f"Generated {_now()}", S["subtitle"]))
    story.append(HRFlowable(width=w, color=BORDER, thickness=1))
    story.append(Spacer(1, 0.3*cm))

    # ---- Summary table -----------------------------------------------------
    story.append(Paragraph("INCIDENT SUMMARY", S["section"]))

    summary_data = [
        ["Field", "Value"],
        ["Incident ID", iid],
        ["Status", status],
        ["Risk Score", f"{risk}/10 — {_risk_label(risk)}"],
        ["Log Source", incident.get("log_source", "unknown")],
        ["Started", incident.get("started_at", "—")],
        ["Completed", incident.get("completed_at", "—")],
        ["Actions Executed", str(len(actions))],
        ["Approval Decision", incident.get("approval_decision", "—").upper()],
    ]

    summary_table = Table(summary_data, colWidths=[4*cm, w - 4*cm])
    summary_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("TEXTCOLOR", (0, 0), (-1, 0), CYAN),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        # Data rows
        ("BACKGROUND", (0, 1), (-1, -1), BG_DARK),
        ("TEXTCOLOR", (0, 1), (0, -1), TEXT_DIM),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (1, 1), (1, -1), TEXT_MAIN),
        # Risk score row highlight
        ("TEXTCOLOR", (1, 3), (1, 3), risk_color),
        ("FONTNAME", (1, 3), (1, 3), "Helvetica-Bold"),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, PANEL]),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.4*cm))

    # ---- Indicators --------------------------------------------------------
    story.append(Paragraph("INDICATORS OF COMPROMISE (IOCs)", S["section"]))
    if indicators:
        ioc_data = [["Indicator", "Type", "Verdict", "Details"]]
        for ind in indicators:
            ti = next((r for r in ti_results if r.get("indicator") == ind), {})
            verdict = "🔴 MALICIOUS" if ti.get("is_malicious") else ("🟢 CLEAN" if ti else "⚪ UNKNOWN")
            itype = "IP Address" if "." in ind and ind.replace(".", "").isdigit() else \
                    "File Hash" if len(ind) in (32, 40, 64) and all(c in "0123456789abcdef" for c in ind.lower()) else \
                    "URL/Domain" if "http" in ind or "/" in ind else "Identifier"
            detail = ti.get("abuse_score") or ti.get("detection_ratio") or "—"
            ioc_data.append([ind[:40], itype, verdict, str(detail)])

        ioc_table = Table(ioc_data, colWidths=[5.5*cm, 2.8*cm, 3*cm, w - 11.3*cm])
        ioc_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("TEXTCOLOR", (0, 0), (-1, 0), CYAN),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 1), (0, -1), "Courier"),
            ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_MAIN),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, PANEL]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(ioc_table)
    else:
        story.append(Paragraph("No indicators of compromise found.", S["body"]))
    story.append(Spacer(1, 0.4*cm))

    # ---- Mitigation Plan ---------------------------------------------------
    story.append(Paragraph("MITIGATION PLAN", S["section"]))
    if plan_text:
        story.append(Paragraph(plan_text, S["body"]))
    else:
        story.append(Paragraph("No mitigation plan available.", S["body"]))
    story.append(Spacer(1, 0.4*cm))

    # ---- Executed Actions --------------------------------------------------
    story.append(Paragraph("EXECUTED ACTIONS", S["section"]))
    if actions:
        action_data = [["#", "Action", "Result"]]
        for i, act in enumerate(actions, 1):
            parts = act.split(" → ")
            action_str = parts[0] if parts else act
            result_str = parts[1] if len(parts) > 1 else "—"
            action_data.append([str(i), action_str, result_str])

        act_table = Table(action_data, colWidths=[1*cm, w - 4*cm, 3*cm])
        act_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PANEL),
            ("TEXTCOLOR", (0, 0), (-1, 0), CYAN),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("FONTNAME", (0, 1), (1, -1), "Courier"),
            ("TEXTCOLOR", (0, 1), (-1, -1), TEXT_MAIN),
            ("TEXTCOLOR", (2, 1), (2, -1), GREEN),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BG_DARK, PANEL]),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ]))
        story.append(act_table)
    else:
        story.append(Paragraph("No actions were executed.", S["body"]))
    story.append(Spacer(1, 0.4*cm))

    # ---- Raw Log -----------------------------------------------------------
    story.append(Paragraph("RAW LOG", S["section"]))
    raw_log = incident.get("raw_log", "No log data available.")
    # Truncate very long logs
    if len(raw_log) > 1500:
        raw_log = raw_log[:1500] + "\n... [truncated]"
    story.append(Paragraph(raw_log.replace("\n", "<br/>"), S["mono"]))

    # Build PDF
    doc.build(story, onFirstPage=_add_page_decorations, onLaterPages=_add_page_decorations)
    return buffer.getvalue()