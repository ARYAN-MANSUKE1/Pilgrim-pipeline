"""
Background job registry + worker for the dashboard.

settings.job_workers threads process jobs FIFO. Costs stay attributed to the
right temple because the in-flight temple id is a ContextVar, not a global
(app/tasks/costs.py). State is persisted to a JSON file, so a server
restart or crash doesn't lose the queue: on startup, any jobs that were queued
or interrupted mid-run are re-queued and resume automatically. Re-running a
temple is safe (translation/audio just overwrite).
"""

from __future__ import annotations

import itertools
import json
import os
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from dashboard.pipeline import process_temple

_STATE = Path(__file__).parent / "jobs_state.json"
_jobs: dict[int, dict] = {}
_q: "queue.Queue[int]" = queue.Queue()
_lock = threading.Lock()
_counter = itertools.count(1)
_started = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _save() -> None:
    """Best-effort persistence — never let a save error affect a job."""
    try:
        # The file write is inside the lock too: with several workers, two
        # concurrent saves could otherwise interleave and truncate the state.
        with _lock:
            _STATE.write_text(json.dumps(_jobs), encoding="utf-8")
    except Exception:
        pass


def _load() -> None:
    global _counter
    if not _STATE.exists():
        return
    try:
        data = json.loads(_STATE.read_text(encoding="utf-8"))
    except Exception:
        return
    with _lock:
        for k, v in data.items():
            _jobs[int(k)] = v
    if _jobs:
        _counter = itertools.count(max(_jobs) + 1)


def enqueue(temple_id, temple_title, operation, languages, source,
            translate_langs=None, audio_langs=None, force=False) -> int:
    jid = next(_counter)
    with _lock:
        _jobs[jid] = {
            "id": jid, "temple_id": temple_id, "temple_title": temple_title,
            "operation": operation, "languages": languages, "source": source,
            "translate_langs": translate_langs, "audio_langs": audio_langs, "force": force,
            "status": "queued", "logs": [], "error": None,
            "queued_at": _now(), "started_at": None, "finished_at": None,
        }
    _q.put(jid)
    _save()
    return jid


def _log(job: dict, msg: str) -> None:
    job["logs"].append(f"{datetime.now().strftime('%H:%M:%S')} {msg}")


def _sync_sheet(job: dict) -> None:
    """Refresh THIS temple's row in the shared tracking sheet -- one WP request,
    not a full-site re-read. Best-effort: the sheet is a report, so neither a
    Google outage nor a WordPress blip may fail or stall a pipeline job."""
    try:
        from dashboard import main, sheet_sync
        if not (settings.google_sa_json and settings.sheet_id):
            return
        sheet_sync.sync(main.sheet_desired_one(job["temple_id"]))
    except Exception as e:  # noqa: BLE001
        _log(job, f"sheet sync skipped: {e}")


def _worker() -> None:
    while True:
        try:
            jid = _q.get()
        except Exception:
            continue
        try:
            job = _jobs.get(jid)
            if job:
                job["status"] = "running"
                job["started_at"] = _now()
                _save()
                try:
                    process_temple(
                        job["temple_id"], job.get("operation", "full"), job.get("languages"),
                        job.get("source"), log=lambda m, j=job: _log(j, m),
                        translate_langs=job.get("translate_langs"),
                        audio_langs=job.get("audio_langs"),
                        force=job.get("force", False),
                    )
                    job["status"] = "done"
                except Exception as e:  # noqa: BLE001 — surface any failure to the UI
                    job["status"] = "failed"
                    job["error"] = str(e)
                    _log(job, f"ERROR: {e}")
                finally:
                    job["finished_at"] = _now()
                    _save()
                    _sync_sheet(job)
        except Exception:
            pass  # a single bad job must never kill the worker thread
        finally:
            try:
                _q.task_done()
            except Exception:
                pass


def start_worker() -> None:
    """Start the background worker. Importing dashboard.main triggers this, so a
    one-off script that imports it for a helper function would otherwise start a
    SECOND worker against the same persisted queue and race the running server.
    Set PILGRIM_NO_WORKER=1 in anything that is not the server."""
    global _started
    if os.environ.get("PILGRIM_NO_WORKER"):
        return
    if _started:
        return
    _started = True
    _load()
    # Resume: re-queue anything that was queued or interrupted mid-run.
    with _lock:
        pending = [jid for jid, j in _jobs.items() if j["status"] in ("queued", "running")]
    for jid in pending:
        _jobs[jid]["status"] = "queued"
        _q.put(jid)
    if pending:
        _save()
    for n in range(1, max(1, settings.job_workers) + 1):
        threading.Thread(target=_worker, daemon=True, name=f"pilgrim-worker-{n}").start()


def all_jobs() -> list[dict]:
    with _lock:
        return sorted(_jobs.values(), key=lambda j: j["id"], reverse=True)


def get_job(jid: int) -> dict | None:
    return _jobs.get(jid)


def clear_finished() -> int:
    with _lock:
        done = [j for j, v in _jobs.items() if v["status"] in ("done", "failed")]
        for j in done:
            del _jobs[j]
    _save()
    return len(done)


def queue_depth() -> int:
    return _q.unfinished_tasks
