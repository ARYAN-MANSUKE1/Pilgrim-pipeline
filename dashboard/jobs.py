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
import logging
import os
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from dashboard.pipeline import Cancelled, process_temple

logger = logging.getLogger(__name__)

_STATE = Path(__file__).parent / "jobs_state.json"
_jobs: dict[int, dict] = {}
_q: "queue.Queue[int]" = queue.Queue()
_lock = threading.Lock()
_counter = itertools.count(1)
_started = False
# Jobs asked to stop. A queued job is cancelled outright; a running one is
# cancelled cooperatively -- Python cannot kill a thread mid-request, so the
# pipeline checks this at safe points and stops there.
_cancelled: set[int] = set()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _save() -> None:
    """Best-effort persistence — never let a save error affect a job.

    Written to a temp file and renamed: write_text truncates first, so killing
    the process mid-write left a half-file that _load() could not parse, and
    the whole job history was silently replaced by an empty one. os.replace is
    atomic, so a crash leaves either the old file or the new one, never a
    truncated one. The lock also serialises concurrent saves from workers.
    """
    try:
        with _lock:
            tmp = _STATE.with_suffix(".tmp")
            tmp.write_text(json.dumps(_jobs), encoding="utf-8")
            os.replace(tmp, _STATE)
    except Exception:
        pass


def _load() -> None:
    global _counter
    if not _STATE.exists():
        return
    try:
        data = json.loads(_STATE.read_text(encoding="utf-8"))
    except Exception:
        # Keep the unreadable file: starting fresh would overwrite it on the
        # next save and destroy the history for good.
        bad = _STATE.with_suffix(".corrupt")
        try:
            os.replace(_STATE, bad)
            logger.error("jobs_state.json unreadable; kept a copy at %s", bad)
        except Exception:
            pass
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


def cancel(jid: int) -> str:
    """Stop one job. Returns what happened, for the UI to report.

    _save() takes _lock itself and threading.Lock is not reentrant, so the
    save happens after the lock is released -- calling it inside deadlocks
    the whole worker pool.
    """
    with _lock:
        job = _jobs.get(jid)
        if not job:
            return "not found"
        status = job["status"]
        if status == "queued":
            job["status"] = "cancelled"
            job["finished_at"] = _now()
            _log(job, "cancelled before it started")
            _cancelled.add(jid)
            result = "cancelled"
        elif status == "running":
            _cancelled.add(jid)
            _log(job, "stop requested - finishing the current step, then stopping")
            result = "stopping"
        else:
            return status
    _save()
    return result


def cancel_all() -> dict:
    """Stop everything queued or running. The queue is drained by the workers,
    which skip anything already marked cancelled."""
    with _lock:
        pending = [j for j in _jobs.values() if j["status"] in ("queued", "running")]
    out = {"cancelled": 0, "stopping": 0}
    for job in pending:
        r = cancel(job["id"])
        if r in out:
            out[r] += 1
    return out


def is_cancelled(jid: int) -> bool:
    return jid in _cancelled


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
            if job and (job["status"] == "cancelled" or jid in _cancelled):
                continue  # cancelled while it sat in the queue
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
                        should_cancel=lambda j=jid: j in _cancelled,
                    )
                    job["status"] = "done"
                except Cancelled as e:
                    job["status"] = "cancelled"
                    _log(job, f"stopped: {e}")
                except Exception as e:  # noqa: BLE001 — surface any failure to the UI
                    job["status"] = "failed"
                    job["error"] = str(e)
                    _log(job, f"ERROR: {e}")
                finally:
                    _cancelled.discard(jid)
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


#: Statuses a job never leaves -- "Clear finished" removes exactly these.
FINISHED = ("done", "failed", "cancelled")


def clear_finished() -> int:
    """Drop every finished job. 'cancelled' counts: it was missing here, so
    stopped jobs piled up in the list with no way to clear them."""
    with _lock:
        done = [j for j, v in _jobs.items() if v["status"] in FINISHED]
        for j in done:
            del _jobs[j]
    _save()
    return len(done)


def queue_depth() -> int:
    """Jobs that will actually run. Cancelled ids stay in the Queue until a
    worker pops and skips them, so unfinished_tasks overstates the backlog and
    left the UI reading "2 in queue" with nothing left to do."""
    with _lock:
        return sum(1 for j in _jobs.values() if j["status"] in ("queued", "running"))
