"""
Guardian Agent — FastAPI Backend v2 with:
  - Email + Slack notifications
  - JWT authentication
  - PDF report export
  - Cron scheduler
"""
from __future__ import annotations
import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Guardian Agent API", version="2.1.0")
app.add_middleware(CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        os.getenv("FRONTEND_URL", ""),
        os.getenv("RAILWAY_STATIC_URL", ""),
        "https://*.railway.app",
        "https://*.vercel.app",
        "*",  # Remove this in production and list exact origins
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=4)
_ws_clients: dict[str, list[WebSocket]] = {}
_main_loop: asyncio.AbstractEventLoop | None = None


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class SubmitLogRequest(BaseModel):
    raw_log: str
    log_source: str = "api"

class LoginRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now():
    return datetime.now(timezone.utc).isoformat()


async def _broadcast(incident_id: str, event: dict[str, Any]):
    import json
    clients = _ws_clients.get(incident_id, []) + _ws_clients.get("*", [])
    dead = []
    for ws in clients:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.append(ws)
    for ws in dead:
        for key in list(_ws_clients.keys()):
            try: _ws_clients[key].remove(ws)
            except ValueError: pass


def _run_agent(incident_id: str, raw_log: str, log_source: str):
    import asyncio
    from app.agent.graph import build_graph
    from app.memory.store import save_incident
    from app.notifications.notifier import notify_incident_created, notify_approval_needed, notify_incident_complete

    initial_state = {
        "messages": [], "raw_log": raw_log,
        "risk_score": 0, "found_indicators": [],
        "requires_approval": False, "mitigation_plan": "",
        "executed_actions": [], "investigation_results": [],
        "current_node": "start", "incident_id": incident_id,
        "log_source": log_source, "status": "analyzing",
        "approval_token": "", "approval_decision": "pending",
        "started_at": _now(), "completed_at": "", "stream_events": [],
    }
    save_incident(initial_state)
    print(f"\n📥 [API] Incident {incident_id} created — starting agent")

    # Notify: incident created
    notify_incident_created(initial_state)

    os.environ["GUARDIAN_MODE"] = "web"
    graph = build_graph()
    config = {"configurable": {"thread_id": incident_id}}

    prev_status = None
    for step in graph.stream(initial_state, config=config, stream_mode="values"):
        events = step.get("stream_events", [])
        for event in events:
            try:
                future = asyncio.run_coroutine_threadsafe(_broadcast(incident_id, event), _main_loop)
                future.result(timeout=2)
            except Exception:
                pass

        # Notify when approval needed
        current_status = step.get("status", "")
        if current_status == "awaiting_approval" and prev_status != "awaiting_approval":
            notify_approval_needed({**initial_state, **step})
        prev_status = current_status

    # Notify: incident complete
    from app.memory.store import get_incident
    final = get_incident(incident_id)
    if final:
        notify_incident_complete(final)


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    global _main_loop
    _main_loop = asyncio.get_event_loop()
    from app.memory.store import init_db
    init_db()
    from app.scheduler.cron import start_scheduler
    start_scheduler()
    print("🛡️  Guardian API v2.1 started")


@app.on_event("shutdown")
async def shutdown():
    from app.scheduler.cron import stop_scheduler
    stop_scheduler()


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    from app.auth.jwt_auth import verify_credentials, create_token
    if not verify_credentials(req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(req.username)
    return {"access_token": token, "token_type": "bearer", "username": req.username}


@app.get("/api/auth/me")
async def auth_me(user=Depends(lambda: None)):
    from app.auth.jwt_auth import get_current_user
    return {"username": "admin", "auth_enabled": os.getenv("GUARDIAN_AUTH_ENABLED", "false")}


# ---------------------------------------------------------------------------
# Dashboard / Stats
# ---------------------------------------------------------------------------

@app.get("/api/stats")
async def get_stats():
    from app.memory.store import get_stats
    return get_stats()


@app.get("/api/state")
async def get_system_state():
    from app.tools.sys_actions import get_current_state
    return get_current_state()


@app.get("/api/scheduler/status")
async def scheduler_status():
    from app.scheduler.cron import get_scheduler_status
    return get_scheduler_status()


@app.post("/api/scheduler/scan")
async def trigger_scan():
    """Manually trigger a scheduler scan."""
    from app.scheduler.cron import scan_and_submit
    asyncio.get_event_loop().run_in_executor(_executor, scan_and_submit)
    return {"message": "Scan triggered"}


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@app.get("/api/incidents")
async def list_incidents(limit: int = 50, offset: int = 0, status: str | None = None, min_risk: int = 0):
    from app.memory.store import list_incidents
    return {"incidents": list_incidents(limit=limit, offset=offset, status=status, min_risk=min_risk)}


@app.get("/api/incidents/pending-approval")
async def pending_approval():
    from app.memory.store import get_pending_approval
    return {"incidents": get_pending_approval()}


@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    from app.memory.store import get_incident
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc


@app.post("/api/incidents", status_code=202)
async def submit_log(req: SubmitLogRequest):
    incident_id = str(uuid.uuid4())
    asyncio.get_event_loop().run_in_executor(_executor, _run_agent, incident_id, req.raw_log, req.log_source)
    return {"incident_id": incident_id, "status": "analyzing"}


@app.post("/api/incidents/{incident_id}/approve")
async def approve_incident(incident_id: str):
    from app.memory.store import set_approval, get_incident
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if inc.get("status") != "awaiting_approval":
        raise HTTPException(status_code=400, detail=f"Incident is not awaiting approval (status: {inc.get('status')})")
    set_approval(incident_id, "approved")
    await _broadcast(incident_id, {"type": "approval_decision", "incident_id": incident_id, "approved": True})
    return {"message": "Approved. Executing mitigation actions."}


@app.post("/api/incidents/{incident_id}/deny")
async def deny_incident(incident_id: str):
    from app.memory.store import set_approval, get_incident
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    if inc.get("status") != "awaiting_approval":
        raise HTTPException(status_code=400, detail=f"Incident is not awaiting approval (status: {inc.get('status')})")
    set_approval(incident_id, "denied")
    await _broadcast(incident_id, {"type": "approval_decision", "incident_id": incident_id, "approved": False})
    return {"message": "Denied. Logging alert only."}


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

@app.get("/api/incidents/{incident_id}/report.pdf")
async def export_pdf(incident_id: str):
    from app.memory.store import get_incident
    from app.reports.generator import generate_incident_pdf
    inc = get_incident(incident_id)
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    try:
        pdf_bytes = generate_incident_pdf(inc)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=guardian-incident-{incident_id[:8]}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws/incidents")
async def websocket_all(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.setdefault("*", []).append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        try: _ws_clients["*"].remove(websocket)
        except ValueError: pass


@app.websocket("/ws/incidents/{incident_id}")
async def websocket_incident(websocket: WebSocket, incident_id: str):
    await websocket.accept()
    _ws_clients.setdefault(incident_id, []).append(websocket)
    from app.memory.store import get_incident
    import json
    inc = get_incident(incident_id)
    if inc:
        await websocket.send_text(json.dumps({"type": "current_state", **inc}))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        try: _ws_clients[incident_id].remove(websocket)
        except ValueError: pass