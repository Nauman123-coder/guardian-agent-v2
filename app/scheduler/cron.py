"""
Guardian Scheduler — Automatic log scanning on a schedule.

Uses APScheduler to run scans at configurable intervals.

Configure via .env:
  SCHEDULER_ENABLED=true
  SCHEDULER_INTERVAL_MINUTES=60       # How often to scan
  SCHEDULER_LOG_DIR=./scheduled_logs  # Directory to watch
  GUARDIAN_API_URL=http://localhost:8000

The scheduler scans the log directory and submits any new/unprocessed
files to the Guardian API automatically.

Usage:
  from app.scheduler.cron import start_scheduler, stop_scheduler
  start_scheduler()  # Call on app startup
  stop_scheduler()   # Call on app shutdown
"""

from __future__ import annotations
import os
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

_scheduler: BackgroundScheduler | None = None
_submitted_hashes: set[str] = set()
_STATE_FILE = Path(os.getenv("GUARDIAN_STATE_DIR", "/tmp")) / "guardian_scheduler_state.json"

WATCH_EXTENSIONS = {".log", ".txt", ".json", ".syslog"}
API_BASE = os.getenv("GUARDIAN_API_URL", "http://localhost:8000")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_state() -> None:
    """Load previously submitted hashes so we don't resubmit on restart."""
    global _submitted_hashes
    if _STATE_FILE.exists():
        try:
            data = json.loads(_STATE_FILE.read_text())
            _submitted_hashes = set(data.get("submitted_hashes", []))
        except Exception:
            pass


def _save_state() -> None:
    try:
        _STATE_FILE.write_text(json.dumps({"submitted_hashes": list(_submitted_hashes), "last_run": _now()}))
    except Exception:
        pass


def _submit_log(content: str, filename: str) -> dict[str, Any] | None:
    try:
        resp = httpx.post(
            f"{API_BASE}/api/incidents",
            json={"raw_log": content, "log_source": f"scheduler:{filename}"},
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        print(f"  ❌ [SCHEDULER] Cannot connect to API at {API_BASE}")
        return None
    except Exception as e:
        print(f"  ❌ [SCHEDULER] Submit error: {e}")
        return None


def scan_and_submit() -> None:
    """Core scan job — runs on every tick."""
    log_dir = Path(os.getenv("SCHEDULER_LOG_DIR", "./scheduled_logs"))
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
        return

    print(f"\n⏰ [SCHEDULER] Scanning {log_dir} at {_now()}")
    found = 0

    for file_path in sorted(log_dir.glob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in WATCH_EXTENSIONS:
            continue

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace").strip()
            if not content:
                continue

            content_hash = hashlib.md5(content.encode()).hexdigest()  # noqa: S324
            if content_hash in _submitted_hashes:
                continue

            print(f"  📄 New log: {file_path.name} ({len(content)} chars)")
            result = _submit_log(content, file_path.name)
            if result:
                incident_id = result.get("incident_id", "?")
                print(f"  ✅ Submitted → Incident {incident_id[:8].upper()}")
                _submitted_hashes.add(content_hash)
                _save_state()
                found += 1

        except Exception as e:
            print(f"  ⚠️  Error reading {file_path.name}: {e}")

    if found == 0:
        print(f"  ℹ️  No new logs found")
    else:
        print(f"  📊 Submitted {found} new log(s)")


def get_scheduler_status() -> dict[str, Any]:
    """Return current scheduler status for the API."""
    interval = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "60"))
    log_dir = os.getenv("SCHEDULER_LOG_DIR", "./scheduled_logs")
    enabled = os.getenv("SCHEDULER_ENABLED", "false").lower() in ("true", "1")

    jobs = []
    if _scheduler and _scheduler.running:
        for job in _scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "next_run": next_run.isoformat() if next_run else None,
            })

    return {
        "enabled": enabled,
        "running": bool(_scheduler and _scheduler.running),
        "interval_minutes": interval,
        "log_dir": log_dir,
        "submitted_count": len(_submitted_hashes),
        "jobs": jobs,
    }


def start_scheduler() -> None:
    """Start the background scheduler. Call on FastAPI startup."""
    global _scheduler

    if os.getenv("SCHEDULER_ENABLED", "false").lower() not in ("true", "1"):
        print("  ℹ️  [SCHEDULER] Disabled (set SCHEDULER_ENABLED=true to enable)")
        return

    _load_state()
    interval = int(os.getenv("SCHEDULER_INTERVAL_MINUTES", "60"))

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        scan_and_submit,
        trigger=IntervalTrigger(minutes=interval),
        id="guardian_scan",
        name="Guardian Log Scanner",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    print(f"  ⏰ [SCHEDULER] Started — scanning every {interval} minute(s)")

    # Run immediately on startup
    scan_and_submit()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        print("  ⏰ [SCHEDULER] Stopped")