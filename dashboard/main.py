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
import logging
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from fastapi import FastAPI, Query
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
        "orderby": "title", "order": "asc",
    }
    if search:
        params["search"] = search
    try:
        r = httpx.get(f"{WP_BASE}/temple", params=params, auth=AUTH, timeout=45)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return {"error": f"Could not reach WordPress: {e}", "total": 0, "pages": 1,
                "page": page, "per_page": per_page, "langs": current_langs,
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
        "langs": current_langs,
        "min_chars": MIN_CHARS,
        "temples": temples,
    }


EXPORT_HEADER = [
    "id", "temple", "link", "source", "text_done", "audio_done",
    "text_count", "audio_count",
    "translation_cost_inr", "audio_cost_inr", "total_cost_inr", "cost_basis",
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20),
       retry=retry_if_exception_type(httpx.HTTPError), reraise=True)
def _fetch_page(page: int, per_page: int = 100):
    """One page of temples. Retried: a 12MB page off the staging host times out
    often enough that losing the whole export to it is not acceptable."""
    r = httpx.get(f"{WP_BASE}/temple", auth=AUTH, timeout=180, params={
        "context": "edit", "page": page, "per_page": per_page,
        "orderby": "title", "order": "asc",
    })
    r.raise_for_status()
    return r


def _csv_row(t: dict, ledger: dict) -> list:
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
        w.writerow(_csv_row(t, ledger))
    yield flush()

    pages = int(first.headers.get("X-WP-TotalPages", 1))
    with ThreadPoolExecutor(max_workers=_EXPORT_WORKERS) as ex:
        for start in range(2, pages + 1, _EXPORT_WORKERS):
            wave = range(start, min(start + _EXPORT_WORKERS, pages + 1))
            for r in ex.map(_fetch_page, wave):
                for t in r.json():
                    w.writerow(_csv_row(t, ledger))
                yield flush()


# Columns of the team's tracking sheet, in its exact order -- including the
# unnamed spacer column and the three approval columns, which export blank for
# the team to fill in by hand.
def sheet_desired(limit: int | None = None) -> list[list]:
    """[[temple_id, name, source, targets, audio, link], ...] in title order --
    what the sheet's data columns should say right now."""
    wp.refresh_language_fields()
    name = lambda l: LANG_NAMES.get(l, l.upper())
    out, page = [], 1
    while True:
        r = _fetch_page(page, per_page=min(limit, 100) if limit else 100)
        for t in r.json():
            st = _status(t.get("acf") or {})
            src = st["source"] or ""
            targets = [l for l, n in st["content"].items() if n >= MIN_CHARS and l != src]
            audio = [l for l, ok in st["audio"].items() if ok]
            title = html.unescape((t.get("title") or {}).get("rendered", "")) or f"Temple {t['id']}"
            out.append([t["id"], title, name(src) if src else "",
                        ", ".join(name(l) for l in targets),
                        ", ".join(name(l) for l in audio), t.get("link", "")])
            if limit and len(out) >= limit:
                return out
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            return out
        page += 1


def _sheet_row_for(t: dict) -> list:
    """One WP temple dict -> the sheet's data columns for it."""
    name = lambda l: LANG_NAMES.get(l, l.upper())
    st = _status(t.get("acf") or {})
    src = st["source"] or ""
    targets = [l for l, n in st["content"].items() if n >= MIN_CHARS and l != src]
    audio = [l for l, ok in st["audio"].items() if ok]
    title = html.unescape((t.get("title") or {}).get("rendered", "")) or f"Temple {t['id']}"
    return [t["id"], title, name(src) if src else "",
            ", ".join(name(l) for l in targets),
            ", ".join(name(l) for l in audio), t.get("link", "")]


def sheet_desired_one(temple_id: int) -> list[list]:
    """Just this temple's row. What the post-job sync uses: re-reading all 2195
    temples (266MB, ~90s) to refresh a single row blocked the job worker for
    minutes at a time and eventually failed outright on a dropped connection."""
    from dashboard.pipeline import _fetch
    return [_sheet_row_for(_fetch(temple_id))]


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
    return {"log": _sync_registry_languages()}


class LanguageReq(BaseModel):
    code: str
    name: str
    native: str | None = None  # pass the existing native name when editing, to skip re-translating it
    fields: bool = False
    chrome: bool = True
    visible: bool = True


@app.get("/api/languages")
def list_languages():
    return language_registry.get_languages()


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
    return {"langs": list(wp.CONTENT_FIELD_KEYS), "names": names}


# no-store: this is an admin tool edited in place, and a browser holding a
# cached page silently hides UI that was just added (the Export CSV button
# showed in one browser and not another until a hard reload).
def _page(name: str) -> FileResponse:
    return FileResponse(STATIC / name, headers={"Cache-Control": "no-store"})


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


jobs.start_worker()
