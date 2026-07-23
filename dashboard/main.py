"""
Pilgrim Pipeline — admin dashboard (FastAPI).

A standalone web tool that sits on top of the pipeline (run_temple / wp_client /
gemini_translate / audio). Phase 1: connect to WordPress and list every temple
with its per-language content + audio status, so you can see at a glance what's
translated/voiced and what still needs work.

Run:  uvicorn dashboard.main:app --reload --port 8000   (then open http://localhost:8000)
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app.tasks import wp_client as wp
from app.tasks.source_detect import detect_source_language, visible_text_length
from dashboard import jobs

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("dashboard")

app = FastAPI(title="Pilgrim Pipeline Dashboard")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")

WP_BASE = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
AUTH = (settings.wp_user, settings.wp_app_password)
ALL_LANGS = ("mr", "en", "hi", "gj", "ta", "te", "ml", "kn")
MIN_CHARS = 200  # visible-text threshold for "filled"


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
    params = {
        "context": "edit", "page": page, "per_page": per_page,
        "orderby": "title", "order": "asc",
    }
    if search:
        params["search"] = search
    try:
        r = httpx.get(f"{WP_BASE}/temple", params=params, auth=AUTH, timeout=45)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return {"error": f"Could not reach WordPress: {e}", "total": 0, "pages": 1,
                "page": page, "per_page": per_page, "langs": list(ALL_LANGS),
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
            **st,
        })
    return {
        "total": int(r.headers.get("X-WP-Total", 0)),
        "pages": int(r.headers.get("X-WP-TotalPages", 1)),
        "page": page,
        "per_page": per_page,
        "langs": list(ALL_LANGS),
        "min_chars": MIN_CHARS,
        "temples": temples,
    }


class TempleRef(BaseModel):
    id: int
    title: str = ""


class RunReq(BaseModel):
    temples: list[TempleRef]
    operation: str = "full"          # translate | audio | full
    languages: list[str] | None = None
    source: str | None = None        # None = auto-detect


@app.post("/api/run")
def run(req: RunReq):
    """Enqueue a background job per selected temple."""
    ids = []
    for t in req.temples:
        jid = jobs.enqueue(t.id, t.title or f"Temple {t.id}", req.operation, req.languages, req.source)
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


@app.post("/api/jobs/clear")
def clear_jobs():
    return {"cleared": jobs.clear_finished()}


@app.get("/api/health")
def health():
    return {"ok": True, "wp": settings.wp_url}


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
    }


class CreateReq(BaseModel):
    title: str
    content: str
    source_lang: str = "mr"
    translate_langs: list[str] = []       # languages to translate into
    audio_langs: list[str] = []           # languages to generate audio for


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

    acf = {content_field: content}
    if title_field:
        acf[title_field] = title
    payload = {
        "title": title,
        "status": "draft",   # always Draft — publishing is done manually in WordPress
        "acf": acf,
    }
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
                       translate_langs=req.translate_langs, audio_langs=req.audio_langs)
    return {"temple_id": pid, "job_id": jid, "link": post.get("link", ""),
            "source_lang": source_lang, "detected": detected}


@app.get("/")
def home():
    return FileResponse(STATIC / "home.html")


@app.get("/process")
def process_page():
    return FileResponse(STATIC / "process.html")


@app.get("/add")
def add_page():
    return FileResponse(STATIC / "add.html")


jobs.start_worker()
