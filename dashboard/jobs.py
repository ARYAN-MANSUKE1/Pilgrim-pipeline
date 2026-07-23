"""
Background job registry + worker for the dashboard.

A single worker thread processes jobs FIFO (sequential = naturally paces API
rate limits and the WP server). State is persisted to a JSON file, so a server
restart or crash doesn't lose the queue: on startup, any jobs that were queued
or interrupted mid-run are re-queued and resume automatically. Re-running a
temple is safe (translation/audio just overwrite).
"""

from __future__ import annotations

import itertools
import json
import queue
import threading
from datetime import datetime, timezone
from pathlib import Path

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
        with _lock:
            data = json.dumps(_jobs)
        _STATE.write_text(data, encoding="utf-8")
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
            translate_langs=None, audio_langs=None) -> int:
    jid = next(_counter)
    with _lock:
        _jobs[jid] = {
            "id": jid, "temple_id": temple_id, "temple_title": temple_title,
            "operation": operation, "languages": languages, "source": source,
            "translate_langs": translate_langs, "audio_langs": audio_langs,
            "status": "queued", "logs": [], "error": None,
            "queued_at": _now(), "started_at": None, "finished_at": None,
        }
    _q.put(jid)
    _save()
    return jid


def _log(job: dict, msg: str) -> None:
    job["logs"].append(f"{datetime.now().strftime('%H:%M:%S')} {msg}")


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
                    )
                    job["status"] = "done"
                except Exception as e:  # noqa: BLE001 — surface any failure to the UI
                    job["status"] = "failed"
                    job["error"] = str(e)
                    _log(job, f"ERROR: {e}")
                finally:
                    job["finished_at"] = _now()
                    _save()
        except Exception:
            pass  # a single bad job must never kill the worker thread
        finally:
            try:
                _q.task_done()
            except Exception:
                pass


def start_worker() -> None:
    global _started
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
    threading.Thread(target=_worker, daemon=True, name="pilgrim-worker").start()


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
