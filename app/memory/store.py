"""
Incident memory store — SQLite-backed persistence for all Guardian incidents.

Provides:
  - save_incident()       : Upsert full incident state
  - get_incident()        : Fetch one incident by ID
  - list_incidents()      : Paginated list with filters
  - get_stats()           : Dashboard summary counts
  - set_approval()        : Write approval decision (used by API)
  - get_pending_approval(): Fetch incidents awaiting human decision
"""

from __future__ import annotations
import json
import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("GUARDIAN_STATE_DIR", "/tmp")) / "guardian_incidents.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id TEXT PRIMARY KEY,
                log_source TEXT,
                raw_log TEXT,
                risk_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                found_indicators TEXT DEFAULT '[]',
                investigation_results TEXT DEFAULT '[]',
                mitigation_plan TEXT DEFAULT '',
                executed_actions TEXT DEFAULT '[]',
                requires_approval INTEGER DEFAULT 0,
                approval_token TEXT,
                approval_decision TEXT DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                stream_events TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON incidents(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_risk ON incidents(risk_score)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_created ON incidents(created_at)")
        conn.commit()


def save_incident(state: dict[str, Any]) -> None:
    """Upsert an incident from agent state."""
    init_db()
    with _connect() as conn:
        conn.execute("""
            INSERT INTO incidents (
                id, log_source, raw_log, risk_score, status,
                found_indicators, investigation_results, mitigation_plan,
                executed_actions, requires_approval, approval_token,
                approval_decision, started_at, completed_at, stream_events
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                risk_score = excluded.risk_score,
                status = excluded.status,
                found_indicators = excluded.found_indicators,
                investigation_results = excluded.investigation_results,
                mitigation_plan = excluded.mitigation_plan,
                executed_actions = excluded.executed_actions,
                requires_approval = excluded.requires_approval,
                approval_token = excluded.approval_token,
                approval_decision = excluded.approval_decision,
                started_at = excluded.started_at,
                completed_at = excluded.completed_at,
                stream_events = excluded.stream_events
        """, (
            state.get("incident_id", ""),
            state.get("log_source", "unknown"),
            state.get("raw_log", ""),
            state.get("risk_score", 0),
            state.get("status", "pending"),
            json.dumps(state.get("found_indicators", [])),
            json.dumps(state.get("investigation_results", [])),
            _strip_actions(state.get("mitigation_plan", "")),
            json.dumps(state.get("executed_actions", [])),
            1 if state.get("requires_approval") else 0,
            state.get("approval_token", ""),
            state.get("approval_decision", "pending"),
            state.get("started_at", ""),
            state.get("completed_at", ""),
            json.dumps(state.get("stream_events", [])),
        ))
        conn.commit()


def get_incident(incident_id: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
        return _row_to_dict(row) if row else None


def list_incidents(
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    min_risk: int = 0,
) -> list[dict[str, Any]]:
    init_db()
    query = "SELECT * FROM incidents WHERE risk_score >= ?"
    params: list[Any] = [min_risk]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]


def get_stats() -> dict[str, Any]:
    init_db()
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        by_status = {
            row["status"]: row["count"]
            for row in conn.execute("SELECT status, COUNT(*) as count FROM incidents GROUP BY status").fetchall()
        }
        high_risk = conn.execute("SELECT COUNT(*) FROM incidents WHERE risk_score >= 7").fetchone()[0]
        pending_approval = conn.execute(
            "SELECT COUNT(*) FROM incidents WHERE status = 'awaiting_approval'"
        ).fetchone()[0]
        avg_risk = conn.execute("SELECT AVG(risk_score) FROM incidents WHERE risk_score > 0").fetchone()[0] or 0
        recent = conn.execute(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        return {
            "total": total,
            "by_status": by_status,
            "high_risk": high_risk,
            "pending_approval": pending_approval,
            "avg_risk_score": round(avg_risk, 1),
            "recent_incidents": [_row_to_dict(r) for r in recent],
        }


def set_approval(incident_id: str, decision: str) -> bool:
    """Set approval decision: 'approved' or 'denied'."""
    init_db()
    with _connect() as conn:
        result = conn.execute(
            "UPDATE incidents SET approval_decision = ?, status = 'executing' WHERE id = ? AND status = 'awaiting_approval'",
            (decision, incident_id),
        )
        conn.commit()
        return result.rowcount > 0


def get_pending_approval() -> list[dict[str, Any]]:
    return list_incidents(status="awaiting_approval")


def _strip_actions(plan: str) -> str:
    """Remove the __ACTIONS__ block before storing — keep only human-readable plan."""
    return plan.split("__ACTIONS__\n")[0] if "__ACTIONS__" in plan else plan


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for field in ("found_indicators", "investigation_results", "executed_actions", "stream_events"):
        try:
            d[field] = json.loads(d.get(field) or "[]")
        except (json.JSONDecodeError, TypeError):
            d[field] = []
    d["requires_approval"] = bool(d.get("requires_approval"))
    # Always expose both 'id' and 'incident_id' so frontend works with either
    if "id" in d and "incident_id" not in d:
        d["incident_id"] = d["id"]
    elif "incident_id" in d and "id" not in d:
        d["id"] = d["incident_id"]
    return d