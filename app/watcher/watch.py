"""
Guardian File Watcher — monitors a directory for new .log / .txt files
and automatically submits them to the Guardian Agent API.

Usage
-----
    python -m app.watcher.watch --dir ./logs --api http://localhost:8000

The watcher uses watchdog to detect file creation events.
It debounces rapidly-written files (waits for them to stop growing)
before submitting to the API.
"""

from __future__ import annotations
import argparse
import os
import time
import hashlib
from pathlib import Path

import httpx
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent


WATCH_EXTENSIONS = {".log", ".txt", ".json", ".syslog"}
DEBOUNCE_SECONDS = float(os.getenv("WATCHER_DEBOUNCE", "2.0"))
API_BASE = os.getenv("GUARDIAN_API_URL", "http://localhost:8000")


class LogFileHandler(FileSystemEventHandler):
    def __init__(self, api_base: str):
        self.api_base = api_base.rstrip("/")
        self._pending: dict[str, float] = {}   # path → last-modified time
        self._submitted: set[str] = set()       # hashes of already-submitted content

    def on_created(self, event: FileCreatedEvent):
        if not event.is_directory:
            self._mark_pending(event.src_path)

    def on_modified(self, event: FileModifiedEvent):
        if not event.is_directory:
            self._mark_pending(event.src_path)

    def _mark_pending(self, path: str):
        if Path(path).suffix.lower() in WATCH_EXTENSIONS:
            self._pending[path] = time.time()

    def flush_pending(self):
        """Call periodically to submit files that have stopped changing."""
        now = time.time()
        ready = [p for p, t in list(self._pending.items()) if now - t >= DEBOUNCE_SECONDS]
        for path in ready:
            del self._pending[path]
            self._submit_file(path)

    def _submit_file(self, path: str):
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace").strip()
            if not content:
                return

            # Deduplicate by content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()  # noqa: S324
            if content_hash in self._submitted:
                print(f"  ⏭️  Skipping duplicate: {path}")
                return
            self._submitted.add(content_hash)

            print(f"\n📂 [WATCHER] New log detected: {path}")
            print(f"   Size: {len(content)} chars  |  Submitting to {self.api_base}")

            resp = httpx.post(
                f"{self.api_base}/api/incidents",
                json={"raw_log": content, "log_source": f"file_watcher:{Path(path).name}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"   ✅ Submitted — Incident ID: {data.get('incident_id', '?')}")
            print(f"   📡 Monitor at: {self.api_base}/api/incidents/{data.get('incident_id')}")

        except httpx.ConnectError:
            print(f"  ❌ Cannot connect to Guardian API at {self.api_base}")
            print(f"     Make sure the API is running: uvicorn app.api.server:app --reload")
        except Exception as exc:
            print(f"  ❌ Error submitting {path}: {exc}")


def watch(watch_dir: str, api_base: str):
    watch_path = Path(watch_dir).resolve()
    watch_path.mkdir(parents=True, exist_ok=True)

    print(f"""
🔭 Guardian File Watcher Started
   Watching : {watch_path}
   API      : {api_base}
   Triggers : {', '.join(WATCH_EXTENSIONS)}
   Debounce : {DEBOUNCE_SECONDS}s

   Drop any .log or .txt file into the watched directory
   to automatically trigger a Guardian analysis.
   Press Ctrl+C to stop.
""")

    handler = LogFileHandler(api_base=api_base)
    observer = Observer()
    observer.schedule(handler, str(watch_path), recursive=False)
    observer.start()

    try:
        while True:
            handler.flush_pending()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n👋 Watcher stopped.")
    finally:
        observer.stop()
        observer.join()


def main():
    parser = argparse.ArgumentParser(description="Guardian File Watcher")
    parser.add_argument("--dir", default="./watched_logs", help="Directory to watch")
    parser.add_argument("--api", default=API_BASE, help="Guardian API base URL")
    args = parser.parse_args()
    watch(args.dir, args.api)


if __name__ == "__main__":
    main()