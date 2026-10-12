"""
Pilgrim Pipeline — admin dashboard (FastAPI).

A standalone web tool that sits on top of the pipeline (run_temple / wp_client /
gemini_translate / audio). Phase 1: connect to WordPress and list every temple
with its per-language content + audio status, so you can see at a glance what's
translated/voiced and what still needs work.

Run:  uvicorn dashboard.main:app --reload --port 8000   (then open http://localhost:8000)
"""

from __future__ import annotations

import csv
import html
import io
import json
import logging
import os
import re
import threading
import time
from datetime import date
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from fastapi import FastAPI, Query, Request
from starlette.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import SARVAM_SUPPORTED_LANGUAGES, settings
from app.tasks import costs
from app.tasks import language_registry
from app.tasks import wp_client as wp
from app.tasks.chrome_sync import sync_chrome_parallel
from app.tasks.nav_menu_i18n import sync_nav_menu_items
from app.tasks.source_detect import detect_source_language, visible_text_length
from dashboard import jobs, sheet_sync

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("dashboard")

app = FastAPI(title="Pilgrim Pipeline Dashboard")


# ── Login ──
# Every page and API call is behind HTTP Basic auth: the dashboard spends real
# Gemini/Sarvam credit and edits the live site, so it must never be open to
# whoever finds the address. No password configured -> localhost only.
# ponytail: one shared login, not per-user accounts; upgrade path is a reverse
# proxy (Cloudflare Access / nginx auth) in front if per-person access is needed.
import base64
import secrets

from fastapi.responses import PlainTextResponse


@app.middleware("http")
async def _require_login(request: Request, call_next):
    if not settings.dashboard_password:
        if request.client and request.client.host in ("127.0.0.1", "::1", "localhost"):
            return await call_next(request)
        return PlainTextResponse("Dashboard password not set (DASHBOARD_PASSWORD in .env) - "
                                 "access is only allowed from the server itself.", status_code=403)
    user, pw = "", ""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("basic "):
        try:
            user, _, pw = base64.b64decode(auth[6:]).decode("utf-8").partition(":")
        except Exception:
            pass
    if secrets.compare_digest(user, settings.dashboard_user) & secrets.compare_digest(pw, settings.dashboard_password):
        return await call_next(request)
    return PlainTextResponse("Login required", status_code=401,
                             headers={"WWW-Authenticate": 'Basic realm="Pilgrim Pipeline"'})
STATIC = Path(__file__).parent / "static"
# no-store on the asset mount too, for the same reason as the pages below: an
# admin tool edited in place must never serve a browser a stale style.css --
# a cached one silently hid the GO button's label.
class _NoCacheStatic(StaticFiles):
    def file_response(self, *a, **kw):
        resp = super().file_response(*a, **kw)
        resp.headers["Cache-Control"] = "no-store"
        return resp


app.mount("/static", _NoCacheStatic(directory=STATIC), name="static")

WP_BASE = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
AUTH = (settings.wp_user, settings.wp_app_password)
# Display-name fallback for the 10 known languages; any language added later
# via the /languages registry gets its name from the registry itself (see
# all_langs() below). The actual language LIST is never hardcoded here --
# it's always wp.CONTENT_FIELD_KEYS, refreshed from the registry on demand.
LANG_NAMES = {
    "mr": "Marathi", "en": "English", "hi": "Hindi", "gj": "Gujarati",
    "ta": "Tamil", "te": "Telugu", "ml": "Malayalam", "kn": "Kannada",
    "bn": "Bengali", "pa": "Punjabi",
}
MIN_CHARS = 200  # visible-text threshold for "filled"
# Add Temple creates DRAFTS; without this they never appeared in the temple list
# or the counts, so a new temple whose job failed could not be found and re-run.
ALL_STATUSES = "publish,draft,pending,private,future"


def _status(acf: dict) -> dict:
    """Per-language content length + audio presence + detected source for one temple."""
    content = {l: visible_text_length(acf.get(f) or "") for l, f in wp.CONTENT_FIELD_KEYS.items()}
    audio = {l: bool(acf.get(af)) for l, af in wp.AUDIO_FIELD_KEYS.items()}
    src = detect_source_language(
        {l: acf.get(f) or "" for l, f in wp.CONTENT_FIELD_KEYS.items()},
        candidates=("mr", "en", "hi"),
    ).source
    return {"content": content, "audio": audio, "source": src}


@app.get("/api/temples")
def list_temples(page: int = 1, per_page: int = Query(20, le=100), search: str = ""):
    """A page of temples with per-language status, straight from WordPress."""
    wp.refresh_language_fields()  # pick up any language added via /languages since last refresh
    current_langs = list(wp.CONTENT_FIELD_KEYS)
    params = {
        "context": "edit", "page": page, "per_page": per_page,
        "orderby": "title", "order": "asc", "status": ALL_STATUSES,
    }
    if search:
        params["search"] = search
    try:
        r = httpx.get(f"{WP_BASE}/temple", params=params, auth=AUTH, timeout=45)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return {"error": f"Could not reach WordPress: {e}", "total": 0, "pages": 1,
                "page": page, "per_page": per_page, "langs": current_langs,
                "audio_enabled": settings.audio_enabled, "names": LANG_NAMES,
                "min_chars": MIN_CHARS, "temples": []}
    temples = []
    for t in r.json():
        acf = t.get("acf") or {}
        st = _status(acf)
        temples.append({
            "id": t["id"],
            "title": (t.get("title") or {}).get("rendered", "") or f"Temple {t['id']}",
            "slug": t.get("slug", ""),
            "link": t.get("link", ""),
            "status": t.get("status", ""),
            **st,
        })
    return {
        "total": int(r.headers.get("X-WP-Total", 0)),
        "pages": int(r.headers.get("X-WP-TotalPages", 1)),
        "page": page,
        "per_page": per_page,
        "langs": current_langs,
        "names": LANG_NAMES,
        "audio_enabled": settings.audio_enabled,
        "min_chars": MIN_CHARS,
        "temples": temples,
    }


EXPORT_HEADER = [
    "id", "temple", "link", "source", "text_done", "audio_done",
    "text_count", "audio_count",
    "translation_cost_inr", "audio_cost_inr", "total_cost_inr", "cost_basis",
    "live_languages", "live_link",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20),
       retry=retry_if_exception_type(httpx.HTTPError), reraise=True)
def _fetch_page(page: int, per_page: int = 100):
    """One page of temples. Retried: a 12MB page off the staging host times out
    often enough that losing the whole export to it is not acceptable."""
    r = httpx.get(f"{WP_BASE}/temple", auth=AUTH, timeout=180, params={
        "context": "edit", "page": page, "per_page": per_page,
        "orderby": "title", "order": "asc", "status": ALL_STATUSES,
    })
    r.raise_for_status()
    return r


def _csv_row(t: dict, ledger: dict, live) -> list:
    acf = t.get("acf") or {}
    st = _status(acf)
    text_done = [l for l, n in st["content"].items() if n >= MIN_CHARS]
    audio_done = [l for l, ok in st["audio"].items() if ok]
    measured = ledger.get(t["id"])
    c = measured or costs.estimate(text_done, audio_done, st["source"] or "")
    tr, au = round(c["translation"], 2), round(c["audio"], 2)
    return [
        t["id"],
        (t.get("title") or {}).get("rendered", "") or f"Temple {t['id']}",
        t.get("link", ""),
        st["source"] or "",
        ",".join(text_done), ",".join(audio_done),
        len(text_done), len(audio_done),
        f"{tr:.2f}", f"{au:.2f}", f"{tr + au:.2f}",
        "measured" if measured else "estimated",
        *(_live_cells(t) if live is SAME_SITE
          else live.get(t.get("slug", ""), [NOT_ON_LIVE, ""]) if live is not None else [LIVE_UNCHECKED, ""]),
    ]


# WP's context=edit returns every ACF field in full -- all ten language bodies,
# ~12MB per 100 temples -- and we need all of it just to measure text length and
# audio presence. 266MB over 22 pages, so the pages are fetched in parallel
# waves instead of one after another (55s -> ~30s).
# ponytail: waves of _EXPORT_WORKERS, not a streaming pool, so at most 3 pages
# (~36MB) sit in memory at once and rows still come out in title order. 3, not
# more: the staging host starts read-timing-out above that. Ceiling: a slow page
# stalls its whole wave. Upgrade path (real fix): a WP-side endpoint
# that returns lengths instead of content, making the whole download ~1MB.
_EXPORT_WORKERS = 3


def _export_rows():
    """Every temple, one CSV chunk at a time, paging WordPress 100 at a time."""
    from concurrent.futures import ThreadPoolExecutor

    wp.refresh_language_fields()
    ledger = costs.totals()
    # Best-effort: the live columns are extra information, so live being slow or
    # unreachable must not cost the user the whole export.
    try:
        # Pointed at live already: the temple being exported IS the live temple, so
        # reading the whole site a second time would only double the wait.
        live = SAME_SITE if _is_live() else _live_index()
    except httpx.HTTPError as e:
        log.warning("export: live site not checked (%s)", e)
        live = None
    buf = io.StringIO()
    w = csv.writer(buf)

    def flush():
        out = buf.getvalue()
        buf.seek(0)
        buf.truncate(0)
        return out

    w.writerow(EXPORT_HEADER)
    # BOM: without it Excel on Windows reads the UTF-8 Devanagari titles as
    # mojibake. Harmless to every other reader.
    yield "﻿" + flush()

    first = _fetch_page(1)
    for t in first.json():
        w.writerow(_csv_row(t, ledger, live))
    yield flush()

    pages = int(first.headers.get("X-WP-TotalPages", 1))
    with ThreadPoolExecutor(max_workers=_EXPORT_WORKERS) as ex:
        for start in range(2, pages + 1, _EXPORT_WORKERS):
            wave = range(start, min(start + _EXPORT_WORKERS, pages + 1))
            for r in ex.map(_fetch_page, wave):
                for t in r.json():
                    w.writerow(_csv_row(t, ledger, live))
                yield flush()


# Columns of the team's tracking sheet, in its exact order -- including the
# unnamed spacer column and the three approval columns, which export blank for
# the team to fill in by hand.
def _sheet_row_for(t: dict) -> list:
    """One WP temple dict -> the sheet's staging columns for it."""
    name = lambda l: LANG_NAMES.get(l, l.upper())
    st = _status(t.get("acf") or {})
    src = st["source"] or ""
    targets = [l for l, n in st["content"].items() if n >= MIN_CHARS and l != src]
    audio = [l for l, ok in st["audio"].items() if ok]
    title = html.unescape((t.get("title") or {}).get("rendered", "")) or f"Temple {t['id']}"
    return [t["id"], title, name(src) if src else "",
            ", ".join(name(l) for l in targets),
            ", ".join(name(l) for l in audio), t.get("link", "")]


# ── The live site, for the sheet's "Live translations" / "Live link" columns ──
# A temple has a different ID on live but the same slug (web address): that is
# how the staging -> live migration matched them, so the sheet matches the same way.
LIVE_BASE = settings.live_wp_url.rstrip("/") + "/wp-json/wp/v2"
LIVE_AUTH = (settings.live_wp_user, settings.live_wp_app_password)
NOT_ON_LIVE = "Not on live"
SAME_SITE = object()  # marker: this dashboard is pointed at the live site itself


def _is_live() -> bool:
    return bool(settings.live_wp_url) and settings.live_wp_url.rstrip("/") == settings.wp_url.rstrip("/")
LIVE_UNCHECKED = "Could not check live"


def _live_cells(t: dict | None) -> list:
    """[languages the live page really has, live link] -- correct-language articles
    only, so a Marathi copy sitting in the Malayalam box is not counted."""
    from app.tasks.safe_translate import content_needs_work
    if not t:
        return [NOT_ON_LIVE, ""]
    acf = t.get("acf") or {}
    langs = [LANG_NAMES.get(l, l.upper()) for l, f in wp.CONTENT_FIELD_KEYS.items()
             if not content_needs_work(acf.get(f) or "", l)]
    return [", ".join(langs) or "none", t.get("link", "")]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20),
       retry=retry_if_exception_type(httpx.HTTPError), reraise=True)
def _live_get(params: dict) -> httpx.Response:
    r = httpx.get(f"{LIVE_BASE}/temple", auth=LIVE_AUTH, timeout=180,
                  params={"context": "edit", "status": ALL_STATUSES, **params})
    r.raise_for_status()
    return r


def _live_index() -> dict[str, list]:
    """{slug: live cells} for every live temple (one full read, ~1 min)."""
    from concurrent.futures import ThreadPoolExecutor
    if not settings.live_wp_url:
        return {}
    first = _live_get({"page": 1, "per_page": 100})
    out = {t["slug"]: _live_cells(t) for t in first.json()}
    pages = int(first.headers.get("X-WP-TotalPages", 1))
    with ThreadPoolExecutor(max_workers=_EXPORT_WORKERS) as ex:
        for r in ex.map(lambda p: _live_get({"page": p, "per_page": 100}), range(2, pages + 1)):
            out.update({t["slug"]: _live_cells(t) for t in r.json()})
    return out


def sheet_desired(limit: int | None = None) -> list[list]:
    """[[temple_id, name, source, targets, audio, link, live_langs, live_link], ...]
    in title order -- what the sheet's data columns should say right now."""
    wp.refresh_language_fields()
    live = _live_index()
    out, page = [], 1
    while True:
        r = _fetch_page(page, per_page=min(limit, 100) if limit else 100)
        for t in r.json():
            out.append(_sheet_row_for(t) + live.get(t.get("slug", ""), [NOT_ON_LIVE, ""]))
            if limit and len(out) >= limit:
                return out
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            return out
        page += 1


def sheet_desired_one(temple_id: int) -> list[list]:
    """Just this temple's row. What the post-job sync uses: re-reading all 2195
    temples (266MB, ~90s) to refresh a single row blocked the job worker for
    minutes at a time and eventually failed outright on a dropped connection."""
    from dashboard.pipeline import _fetch
    t = _fetch(temple_id)
    live = None
    if settings.live_wp_url and t.get("slug"):
        found = _live_get({"slug": t["slug"]}).json()
        live = found[0] if found else None
    return [_sheet_row_for(t) + _live_cells(live)]


@app.post("/api/sync-sheet")
def sync_sheet(limit: int | None = Query(None, ge=1, le=2000)):
    """Push current progress into the shared Google Sheet (columns D/E only)."""
    try:
        return sheet_sync.sync(sheet_desired(limit or settings.sheet_limit or None))
    except Exception as e:  # noqa: BLE001 -- surface the reason in the UI
        return {"error": str(e)}


@app.get("/api/export.csv")
def export_csv():
    """Full temple list + per-temple cost, as a CSV download.

    Cost is measured from the ledger (app/tasks/costs.py) for temples processed
    since cost logging was added; anything older has no rows, so its cost falls
    back to the per-language averages in full-site-cost.pdf and the row is
    marked "estimated".
    """
    # Buffered, not streamed: the whole CSV is ~460KB, so joining it costs
    # nothing and gives the browser a Content-Length -- otherwise the download
    # shows an ever-growing size with no total, which reads like a hang.
    return Response(
        content="".join(_export_rows()),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pilgrim-temples.csv"'},
    )


class TempleRef(BaseModel):
    id: int
    title: str = ""


class RunReq(BaseModel):
    temples: list[TempleRef]
    operation: str = "full"          # translate | audio | full -- used only if translate_langs/audio_langs are both absent
    languages: list[str] | None = None
    source: str | None = None        # None = auto-detect per temple
    translate_langs: list[str] | None = None  # granular: exactly these languages get translated
    audio_langs: list[str] | None = None      # granular: exactly these languages get voiced
    # If translate_langs/audio_langs are given, they win over operation/languages --
    # same precedence pipeline.process_temple() already uses for Add Temple.
    force: bool = False  # deliberately overwrite languages that already have content


@app.post("/api/run")
def run(req: RunReq):
    """Enqueue a background job per selected temple."""
    if not settings.audio_enabled:
        if req.translate_langs is None and req.audio_langs is None:
            if req.operation == "audio":
                return {"error": AUDIO_OFF, "queued": 0, "job_ids": []}
        else:
            req.audio_langs = []
            if not req.translate_langs:
                return {"error": AUDIO_OFF, "queued": 0, "job_ids": []}
    if not req.temples:
        return {"error": "Select at least one temple first.", "queued": 0, "job_ids": []}
    ids = []
    for t in req.temples:
        jid = jobs.enqueue(
            t.id, t.title or f"Temple {t.id}", req.operation, req.languages, req.source,
            translate_langs=req.translate_langs, audio_langs=req.audio_langs, force=req.force,
        )
        ids.append(jid)
    return {"job_ids": ids, "queued": len(ids)}


@app.get("/api/jobs")
def list_jobs():
    out = []
    for j in jobs.all_jobs():
        out.append({
            "id": j["id"], "temple_id": j["temple_id"], "temple_title": j["temple_title"],
            "operation": j["operation"], "languages": j["languages"], "source": j["source"],
            "status": j["status"], "error": j["error"],
            "last": j["logs"][-1] if j["logs"] else "",
            "queued_at": j["queued_at"], "started_at": j["started_at"], "finished_at": j["finished_at"],
        })
    return {"jobs": out, "queue_depth": jobs.queue_depth()}


@app.get("/api/jobs/{jid}")
def job_detail(jid: int):
    return jobs.get_job(jid) or {"error": "not found"}


@app.post("/api/jobs/cancel-all")
def cancel_all_jobs():
    """Stop every queued and running job. Queued jobs stop immediately; running
    ones stop at their next safe point, after saving work already paid for."""
    return jobs.cancel_all()


@app.post("/api/jobs/{jid}/cancel")
def cancel_job(jid: int):
    """Stop one job, queued or running."""
    return {"id": jid, "result": jobs.cancel(jid)}


@app.post("/api/jobs/clear")
def clear_jobs():
    return {"cleared": jobs.clear_finished()}


@app.get("/api/health")
def health():
    return {"ok": True, "wp": settings.wp_url}


# ── What is left to do, per language ──
# Needs every temple's full ACF (~266MB off WordPress, about a minute), so it is
# counted in the background -- at startup, every BACKLOG_EVERY seconds, when the
# job queue empties, and on "Refresh" -- and the last result is kept on disk so
# a restart shows numbers immediately.
# ponytail: a full re-count each time, not per-temple updates; fine at ~2,300
# temples. Upgrade path: a WP-side endpoint returning field lengths only.
AUDIO_OFF = ("Audio generation is switched off for now. To turn it on, set AUDIO_ENABLED=1 "
             "in the .env file and restart the dashboard.")
BACKLOG_FILE = Path(__file__).parent / "backlog.json"
BACKLOG_EVERY = 30 * 60
_backlog: dict = {"counted_at": None, "counting": False, "error": None, "data": None}
try:
    _saved = json.loads(BACKLOG_FILE.read_text(encoding="utf-8"))
    # Counts (and the temple ids behind "Translate all") from another website must
    # never be shown or queued here -- e.g. staging's numbers after switching to live.
    if _saved.get("site") == settings.wp_url:
        _backlog.update(_saved)
    _backlog["counting"] = False
except Exception:
    pass


def _count_backlog() -> dict:
    from concurrent.futures import ThreadPoolExecutor
    from app.tasks.safe_translate import content_needs_work

    wp.refresh_language_fields()
    langs = list(wp.CONTENT_FIELD_KEYS)
    by_lang = {l: {"text": 0, "audio": 0} for l in langs}
    d = {"total": 0, "complete": 0, "need_text": 0, "need_audio": 0, "no_source": 0,
         "text_units": 0, "audio_units": 0}
    todo = {"text": [], "audio": []}  # [id, title, source] -- what "Queue all" sends

    def tally(r):
        for t in r.json():
            acf = t.get("acf") or {}
            d["total"] += 1
            src = _status(acf)["source"]
            if not src:
                d["no_source"] += 1  # nothing to translate from: needs content first
                continue
            text = [l for l in langs if content_needs_work(acf.get(wp.CONTENT_FIELD_KEYS[l]) or "", l)]
            audio = [l for l in langs if wp.AUDIO_FIELD_KEYS.get(l) and not acf.get(wp.AUDIO_FIELD_KEYS[l])]
            ref = [t["id"], html.unescape((t.get("title") or {}).get("rendered", "")) or f"Temple {t['id']}", src]
            for l in text:
                by_lang[l]["text"] += 1
            for l in audio:
                by_lang[l]["audio"] += 1
            if text:
                todo["text"].append(ref)
            if audio:
                todo["audio"].append(ref)
            d["text_units"] += len(text)
            d["audio_units"] += len(audio)
            d["need_text"] += bool(text)
            d["need_audio"] += bool(audio)
            d["complete"] += not (text or audio)

    first = _fetch_page(1)
    tally(first)
    pages = int(first.headers.get("X-WP-TotalPages", 1))
    with ThreadPoolExecutor(max_workers=_EXPORT_WORKERS) as ex:
        for r in ex.map(_fetch_page, range(2, pages + 1)):
            tally(r)
    names = {l: LANG_NAMES.get(l, l.upper()) for l in langs}
    return {**d, "by_lang": by_lang, "names": names, "todo": todo}


def refresh_backlog_async() -> bool:
    """Start a background count unless one is already running."""
    if _backlog["counting"]:
        return False
    _backlog["counting"] = True

    def run():
        try:
            _backlog["data"] = _count_backlog()
            _backlog["counted_at"] = jobs._now()
            _backlog["error"] = None
            _backlog["site"] = settings.wp_url
            BACKLOG_FILE.write_text(json.dumps(_backlog), encoding="utf-8")
        except Exception as e:  # noqa: BLE001 -- shown on the Home page
            _backlog["error"] = f"Could not count temples: {e}"
        finally:
            _backlog["counting"] = False

    threading.Thread(target=run, daemon=True, name="pilgrim-backlog").start()
    return True


def _backlog_loop():
    while True:
        refresh_backlog_async()
        time.sleep(BACKLOG_EVERY)


@app.post("/api/backlog/refresh")
def backlog_refresh():
    return {"started": refresh_backlog_async()}


class BacklogRunReq(BaseModel):
    kind: str  # "text" | "audio"


@app.post("/api/run_backlog")
def run_backlog(req: BacklogRunReq):
    """Queue every temple the last count found still needing translation (or audio).
    The pipeline only fills what is missing, so every language can be asked for.
    Temples already queued or running are not queued twice."""
    if req.kind == "audio" and not settings.audio_enabled:
        return {"error": AUDIO_OFF}
    data = _backlog.get("data") or {}
    refs = (data.get("todo") or {}).get(req.kind)
    if req.kind not in ("text", "audio") or refs is None:
        return {"error": "Nothing counted yet - wait for the count to finish, or press Refresh."}
    busy = {j["temple_id"] for j in jobs.all_jobs() if j["status"] in ("queued", "running")}
    langs = list(wp.CONTENT_FIELD_KEYS)
    queued = 0
    for tid, title, *src in refs:
        if tid in busy:
            continue
        # Source pinned to what it was when counted: the pipeline's own pick is
        # Marathi first, so after a half-finished run on an English-original temple
        # a re-run would translate from the freshly machine-made Marathi.
        jobs.enqueue(tid, title, "translate" if req.kind == "text" else "audio", None, (src or [None])[0],
                     translate_langs=langs if req.kind == "text" else [],
                     audio_langs=langs if req.kind == "audio" else [])
        queued += 1
    return {"queued": queued, "skipped_already_queued": len(refs) - queued}


@app.post("/api/resume")
def resume_queue():
    """After topping up the provider: start the paused queue again."""
    return {"waiting": jobs.resume()}


@app.get("/api/stats")
def stats():
    try:
        r = httpx.get(f"{WP_BASE}/temple", params={"per_page": 1}, auth=AUTH, timeout=30)
        total = int(r.headers.get("X-WP-Total", 0))
        wp_ok = True
    except httpx.HTTPError:
        total, wp_ok = 0, False
    js = jobs.all_jobs()
    return {
        "total_temples": total,
        "wp_ok": wp_ok,
        "jobs_done": sum(1 for j in js if j["status"] == "done"),
        "jobs_failed": sum(1 for j in js if j["status"] == "failed"),
        "queue_depth": jobs.queue_depth(),
        "paused": jobs.paused(),
        "audio_enabled": settings.audio_enabled,
        "site": settings.wp_url,
        "spent_today": costs.spent_on(date.today().isoformat()),
        "per_language_inr": costs.per_language_inr(),
        # the to-do id lists stay server-side: the page only needs the counts
        "backlog": {**_backlog, "data": {k: v for k, v in (_backlog.get("data") or {}).items() if k != "todo"} or None},
    }


class CreateReq(BaseModel):
    title: str
    content: str
    source_lang: str = "mr"
    translate_langs: list[str] = []       # languages to translate into
    audio_langs: list[str] = []           # languages to generate audio for
    photo_ids: list[int] = []             # already uploaded via /api/upload_image; first = cover


@app.post("/api/create_temple")
def create_temple(req: CreateReq):
    """Create a temple in WordPress from source content, then enqueue the pipeline."""
    from app.tasks.structured_translate import strip_cosmetic_spans, strip_tags

    title = (req.title or "").strip()
    content = strip_cosmetic_spans((req.content or "").strip())

    # --- validation first (so we never waste a detection call on bad input) ---
    if not title:
        return {"error": "Title is required."}
    if len(strip_tags(content)) < MIN_CHARS:
        return {"error": f"Content is too short — add at least ~{MIN_CHARS} characters of text "
                         "so the pipeline recognises it as real content (not a placeholder)."}

    # --- resolve source language: only auto-detect when the user picked "Other" ---
    from app.tasks.field_checks import content_problem
    detected = None
    source_lang = req.source_lang
    if source_lang == "other":
        from app.tasks.gemini_translate import detect_language
        detected = detect_language(content)
        if not detected:
            return {"error": "Couldn't detect the content's language — please pick the source language manually."}
        source_lang = detected

    content_field = wp.CONTENT_FIELD_KEYS.get(source_lang)
    title_field = wp.TITLE_FIELD_KEYS.get(source_lang)
    if not content_field:
        return {"error": f"Unsupported source language: {source_lang!r}."}
    # Checked before anything is created: the pipeline refuses a source in the wrong
    # language, which used to leave an empty draft behind in WordPress.
    problem = content_problem(content, source_lang)
    if problem and problem != "token leak":
        name = LANG_NAMES.get(source_lang, source_lang)
        return {"error": f"This text doesn't look like {name} ({problem}). "
                         f"Pick the language it is actually written in, or 'Other' to detect it."}

    acf = {content_field: content}
    if title_field:
        acf[title_field] = title
    if req.photo_ids:
        acf["gallery"] = req.photo_ids          # the temple page's photo slider
    payload = {
        "title": title,
        "status": "draft",   # always Draft — publishing is done manually in WordPress
        "acf": acf,
    }
    if req.photo_ids:
        payload["featured_media"] = req.photo_ids[0]  # cover image
    try:
        r = httpx.post(f"{WP_BASE}/temple", json=payload, auth=AUTH, timeout=45)
    except httpx.HTTPError as e:
        return {"error": f"Could not reach WordPress: {e}"}
    if r.status_code not in (200, 201):
        return {"error": f"WordPress create failed ({r.status_code}): {r.text[:200]}"}
    post = r.json()
    pid = post["id"]
    op_label = "+".join(x for x in ("translate" if req.translate_langs else "",
                                    "audio" if req.audio_langs else "") if x) or "none"
    jid = jobs.enqueue(pid, title, op_label, None, source_lang,
                       translate_langs=req.translate_langs,
                       audio_langs=req.audio_langs if settings.audio_enabled else [])
    return {"temple_id": pid, "job_id": jid, "link": post.get("link", ""),
            "edit_link": f"{settings.wp_url.rstrip('/')}/wp-admin/post.php?post={pid}&action=edit",
            "source_lang": source_lang, "detected": detected}


def _sync_registry_languages() -> list[str]:
    """Sync nav menu + chrome to whatever the registry currently says (chrome=true set)."""
    langs = language_registry.get_languages()
    chrome_langs = [code for code, l in langs.items() if l.get("chrome")]
    log: list[str] = []
    try:
        log += sync_nav_menu_items(chrome_langs)
    except Exception as e:
        log.append(f"Nav menu sync FAILED: {e}")
    log += sync_chrome_parallel(chrome_langs)
    return log


@app.post("/api/sync_languages")
def sync_languages():
    """
    Re-sync nav menu + footer/header chrome to match the language registry's
    current chrome=true set (add missing, drop removed). Runs in parallel,
    not one language at a time -- see /api/languages for adding a language.
    """
    try:
        return {"log": _sync_registry_languages()}
    except httpx.HTTPError:
        return {"log": [REGISTRY_MISSING]}


class LanguageReq(BaseModel):
    code: str
    name: str
    native: str | None = None  # pass the existing native name when editing, to skip re-translating it
    fields: bool = False
    chrome: bool = True
    visible: bool = True


# The registry endpoint (pilgrim/v1/languages) was part of the old Hello Elementor
# theme and is not in the current pilgrim-data-services theme, whose 10 languages
# are built into inc/template-tags.php. Say so instead of crashing with a 500.
REGISTRY_MISSING = ("The website's current theme has no language registry (pilgrim/v1/languages), so languages can't be "
                    "added or changed from here. The site's 10 languages are built into the theme.")


@app.get("/api/languages")
def list_languages():
    try:
        return language_registry.get_languages()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"error": REGISTRY_MISSING}
        return {"error": f"WordPress refused the request ({e.response.status_code})."}
    except httpx.HTTPError as e:
        return {"error": f"Could not reach WordPress: {e}"}


@app.post("/api/languages")
def add_language(req: LanguageReq):
    """
    Add or update one language's flags in the registry. This ONLY saves --
    it does not trigger the nav/chrome sync, even if chrome=true, because that
    sync is slow (translates every chrome-enabled language) and most saves
    here are just flipping one flag (e.g. turning on ACF fields), not
    changing anything nav/chrome-related. Use "Re-sync nav & chrome now"
    (POST /api/sync_languages) explicitly when you actually want that to run.
    """
    try:
        language_registry.save_language(
            req.code, req.name, native=req.native, fields=req.fields, chrome=req.chrome, visible=req.visible
        )
    except Exception as e:
        return {"log": [f"FAILED to save language: {e}"]}

    log = [f"[{req.code}] saved to registry"]
    if req.fields:
        log.append(f"[{req.code}] ACF fields will appear on the temple editor's next WP page load")
    if req.chrome:
        log.append(f"[{req.code}] chrome is on but NOT synced yet -- click \"Re-sync nav & chrome now\" to apply it")
    return {"log": log}


@app.get("/api/sarvam_languages")
def sarvam_languages():
    """
    Sarvam Bulbul's complete, verified supported-language list (code -> {sarvam_code, name}).
    Feeds the Add Language dropdown so a client can only pick a language Sarvam
    can actually voice -- no free-text code entry, no possibility of the
    "Unsupported language" failure this replaces. Excludes the 'gu' alias
    (identical to 'gj', which is the site's convention) so each language
    appears once.
    """
    return {
        code: {"sarvam_code": sc, "name": name}
        for code, (sc, name) in SARVAM_SUPPORTED_LANGUAGES.items()
        if code != "gu"
    }


@app.get("/api/all_langs")
def all_langs():
    """The pipeline's currently-usable language codes + display names, for
    pages (like Add Temple) that have no other API call to piggyback this on."""
    wp.refresh_language_fields()  # pick up any language added via /languages since last refresh
    names = dict(LANG_NAMES)
    try:
        for code, lang in language_registry.get_languages().items():
            names.setdefault(code, lang.get("name", code))
    except Exception:
        pass  # registry unreachable -- fall back to the static names we already have
    return {"langs": list(wp.CONTENT_FIELD_KEYS), "names": names, "audio_enabled": settings.audio_enabled}



# ── Photo upload (Add Temple photos, ad images) ──
# One file per request, raw bytes in the body: no multipart dependency, and the
# page can show progress photo by photo. Passed straight on to WordPress media.
_IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024


@app.post("/api/upload_image")
async def upload_image(request: Request, name: str = ""):
    ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype not in _IMAGE_TYPES:
        return {"error": "Only JPG, PNG, WebP or GIF images can be uploaded."}
    data = await request.body()
    if not data:
        return {"error": "The file is empty."}
    if len(data) > MAX_IMAGE_BYTES:
        return {"error": f"{name or 'This photo'} is over 15 MB - please use a smaller copy."}
    # HTTP headers must be ASCII, so a Marathi file name becomes a plain one.
    stem = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")[:60] or "photo"
    try:
        mid = await run_in_threadpool(wp.upload_media, data, f"{stem}.{_IMAGE_TYPES[ctype]}", ctype)
    except httpx.HTTPError as e:
        return {"error": f"WordPress did not accept the photo: {e}"}
    return {"id": mid}


# ── Ad campaigns (the Advertisements post type on the site) ──
# Fields are read and written as post meta, exposed to logged-in users only by
# the theme (functions.php "Ad fields ... for the dashboard's Ads tab").
AD_PLACEMENTS = {"temple_top": "Top banner", "temple_left": "Left column", "temple_right": "Right column",
                 "temple_bottom": "Bottom banner"}
AD_STATUSES = ("active", "paused", "draft", "scheduled", "pending_payment", "expired")
_AD_META = ("advertiser_name", "ad_creative", "destination_url", "start_date", "end_date",
            "target_cities", "placement", "campaign_status", "campaign_price")


def _ymd_to_iso(v) -> str:
    v = str(v or "")
    if re.fullmatch(r"\d{8}", v):
        return f"{v[:4]}-{v[4:6]}-{v[6:]}"
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v):
        return f"{v[6:]}-{v[3:5]}-{v[:2]}"
    return v


def _ad_state(meta: dict, post_status: str) -> str:
    """What a visitor sees right now: running / scheduled / ended / paused / not running."""
    if post_status != "publish" or meta.get("campaign_status") != "active":
        return "paused" if meta.get("campaign_status") == "paused" else "not running"
    today = date.today().isoformat()
    start, end = _ymd_to_iso(meta.get("start_date")), _ymd_to_iso(meta.get("end_date"))
    if start and today < start:
        return "scheduled"
    if end and today > end:
        return "ended"
    return "running"


@app.get("/api/cities")
def cities():
    """States (top-level terms) with their districts, for ad targeting."""
    out, page = [], 1
    while True:
        r = httpx.get(f"{WP_BASE}/city", params={"per_page": 100, "page": page, "_fields": "id,name,parent"},
                      auth=AUTH, timeout=60)
        r.raise_for_status()
        out += r.json()
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            break
        page += 1
    states = sorted((t for t in out if not t["parent"]), key=lambda t: t["name"])
    return [{"id": s["id"], "name": html.unescape(s["name"]),
             "districts": sorted(({"id": t["id"], "name": html.unescape(t["name"])} for t in out if t["parent"] == s["id"]),
                                 key=lambda t: t["name"])}
            for s in states]


@app.get("/api/ads")
def list_ads():
    try:
        r = httpx.get(f"{WP_BASE}/advertisements", auth=AUTH, timeout=60, params={
            "context": "edit", "per_page": 100, "status": ALL_STATUSES, "orderby": "date", "order": "desc"})
        r.raise_for_status()
    except httpx.HTTPError as e:
        return {"error": f"Could not reach WordPress: {e}", "ads": []}
    posts = r.json()
    # The theme exposes the fields; an older theme leaves "meta" without them.
    if posts and not any("placement" in (p.get("meta") or {}) for p in posts):
        return {"error": "The website's theme doesn't share the ad fields yet - paste the latest functions.php "
                         "(it adds \"Ad fields for the dashboard's Ads tab\").", "ads": []}
    image_ids = {int((p.get("meta") or {}).get("ad_creative") or 0) for p in posts} - {0}
    images = {}
    if image_ids:
        m = httpx.get(f"{WP_BASE}/media", auth=AUTH, timeout=60, params={
            "include": ",".join(map(str, image_ids)), "per_page": 100, "_fields": "id,source_url"})
        if m.status_code == 200:
            images = {x["id"]: x["source_url"] for x in m.json()}
    ads = []
    for p in posts:
        meta = p.get("meta") or {}
        ads.append({
            "id": p["id"], "post_status": p["status"],
            **{k: meta.get(k) for k in _AD_META},
            "start_date": _ymd_to_iso(meta.get("start_date")), "end_date": _ymd_to_iso(meta.get("end_date")),
            "image_url": images.get(int(meta.get("ad_creative") or 0), ""),
            "impressions": int(meta.get("_ad_impressions") or 0), "clicks": int(meta.get("_ad_clicks") or 0),
            "state": _ad_state(meta, p["status"]),
        })
    return {"ads": ads, "placements": AD_PLACEMENTS}


class AdReq(BaseModel):
    advertiser_name: str
    ad_creative: int = 0
    destination_url: str = ""
    start_date: str = ""          # YYYY-MM-DD
    end_date: str = ""
    target_cities: list[int] = []
    placement: str = ""
    campaign_status: str = "active"
    campaign_price: float = 0


def _save_ad(req: AdReq, ad_id: int | None) -> dict:
    if not req.advertiser_name.strip():
        return {"error": "Advertiser name is required."}
    if req.placement not in AD_PLACEMENTS:
        return {"error": "Pick where the ad goes: top banner, left or right column, or bottom banner."}
    if req.campaign_status not in AD_STATUSES:
        return {"error": f"Unknown status {req.campaign_status!r}."}
    if not req.ad_creative:
        return {"error": "Upload the ad image."}
    if not req.target_cities:
        return {"error": "Pick at least one state or district - an ad with no cities is never shown."}
    if req.start_date and req.end_date and req.end_date < req.start_date:
        return {"error": "The end date is before the start date."}
    if req.destination_url and not re.match(r"https?://", req.destination_url):
        return {"error": "The link must start with http:// or https://"}
    meta = req.model_dump()
    meta["start_date"] = req.start_date.replace("-", "")   # stored the way SCF stores dates: Ymd
    meta["end_date"] = req.end_date.replace("-", "")
    meta["target_cities"] = [str(c) for c in req.target_cities]
    body = {"title": req.advertiser_name.strip(), "status": "publish", "meta": meta}
    url = f"{WP_BASE}/advertisements" + (f"/{ad_id}" if ad_id else "")
    try:
        r = httpx.post(url, json=body, auth=AUTH, timeout=60)
    except httpx.HTTPError as e:
        return {"error": f"Could not reach WordPress: {e}"}
    if r.status_code not in (200, 201):
        return {"error": f"WordPress refused the save ({r.status_code}): {r.text[:200]}"}
    saved = r.json()
    # WordPress silently drops fields the theme has not registered. Without this check
    # an older functions.php would leave a published, empty campaign behind.
    if (saved.get("meta") or {}).get("placement") != req.placement:
        if not ad_id:
            httpx.delete(f"{WP_BASE}/advertisements/{saved['id']}", params={"force": "true"}, auth=AUTH, timeout=60)
        return {"error": "The website did not save the campaign's details - its theme (functions.php) is missing the "
                         "\"Ad fields for the dashboard's Ads tab\" code. Nothing was created."}
    return {"id": saved["id"]}


@app.post("/api/ads")
def create_ad(req: AdReq):
    return _save_ad(req, None)


@app.post("/api/ads/{ad_id}")
def update_ad(ad_id: int, req: AdReq):
    return _save_ad(req, ad_id)


class AdStatusReq(BaseModel):
    campaign_status: str


@app.post("/api/ads/{ad_id}/status")
def set_ad_status(ad_id: int, req: AdStatusReq):
    """Pause / activate without touching anything else."""
    if req.campaign_status not in AD_STATUSES:
        return {"error": f"Unknown status {req.campaign_status!r}."}
    r = httpx.post(f"{WP_BASE}/advertisements/{ad_id}", json={"meta": {"campaign_status": req.campaign_status}},
                   auth=AUTH, timeout=60)
    return {"ok": True} if r.status_code == 200 else {"error": f"WordPress refused ({r.status_code}): {r.text[:150]}"}


@app.delete("/api/ads/{ad_id}")
def delete_ad(ad_id: int):
    """Move to the WordPress trash (restorable there for 30 days)."""
    r = httpx.delete(f"{WP_BASE}/advertisements/{ad_id}", auth=AUTH, timeout=60)
    return {"ok": True} if r.status_code == 200 else {"error": f"WordPress refused ({r.status_code})"}


# no-store: this is an admin tool edited in place, and a browser holding a
# cached page silently hides UI that was just added (the Export CSV button
# showed in one browser and not another until a hard reload).
def _page(name: str) -> FileResponse:
    return FileResponse(STATIC / name, headers={"Cache-Control": "no-store"})


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/")
def home():
    return _page("home.html")


@app.get("/process")
def process_page():
    return _page("process.html")


@app.get("/add")
def add_page():
    return _page("add.html")


@app.get("/languages")
def languages_page():
    return _page("languages.html")


@app.get("/ads")
def ads_page():
    return _page("ads.html")


jobs.start_worker()
if not os.environ.get("PILGRIM_NO_WORKER"):  # same guard as the job worker: server only
    threading.Thread(target=_backlog_loop, daemon=True, name="pilgrim-backlog-loop").start()
