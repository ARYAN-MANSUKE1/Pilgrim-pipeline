"""
Translate the temples on LIVE that are missing languages (the live-only
temples that were never on staging), using the checked pipeline in
dashboard/pipeline.py. Text only -- no audio.

    python translate_live.py                  # dry run: lists the temples and what each needs; no Gemini, no writes
    python translate_live.py --go --only 3    # translate 3 temples (test the path)
    python translate_live.py --go             # all of them
    python translate_live.py --go --temple 36595
    python translate_live.py --go --budget 300   # stop once Rs300 has been spent

Every temple is read back from live after it is saved and each language is
re-checked ("verified 9/9"). A temple that fails is logged and the run moves
on; running out of provider credit stops the run at once. Safe to re-run:
languages that are already correct are never touched, and the source stays
English on a re-run (see SOURCE below), so nothing is translated from a
machine translation.
"""

from __future__ import annotations

import json
import sys
import threading
import time

from app.config import settings

# Point the pipeline at LIVE. dashboard/pipeline.py and wp_client read these at
# import / call time, so this must happen before either is imported.
settings.wp_url = settings.live_wp_url
settings.wp_user = settings.live_wp_user
settings.wp_app_password = settings.live_wp_app_password

import httpx  # noqa: E402

import dashboard.pipeline as pipe  # noqa: E402
from app.tasks import costs, wp_client as wp  # noqa: E402
from app.tasks.field_checks import MIN_CHARS, content_problem, visible  # noqa: E402
from app.tasks.safe_translate import content_needs_work, title_needs_work  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

GO = "--go" in sys.argv
ONLY = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None
TEMPLE = int(sys.argv[sys.argv.index("--temple") + 1]) if "--temple" in sys.argv else None
BUDGET = float(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else None
LOG = "translate_live_log.jsonl"
API = settings.live_wp_url.rstrip("/") + "/wp-json/wp/v2/temple"
AUTH = (settings.live_wp_user, settings.live_wp_app_password)
CF, TF = wp.CONTENT_FIELD_KEYS, wp.TITLE_FIELD_KEYS
# English is the original on these temples. Pinned so a re-run after a partial
# failure does not pick the freshly machine-translated Marathi as its source
# (the pipeline's staging rule is Marathi-first).
SOURCE = "en"

_spend = {"in": 0, "out": 0, "calls": 0}
_lock = threading.Lock()


def _track(usage, lang=""):
    if usage:
        with _lock:
            _spend["in"] += int(usage.get("promptTokenCount") or 0)
            _spend["out"] += int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0)
            _spend["calls"] += 1


costs.record_translation = _track


def spent():
    with _lock:
        return costs.translation_inr(_spend["in"], _spend["out"])


def get(url, **params):
    for attempt in range(6):
        try:
            r = httpx.get(url, auth=AUTH, params=params, timeout=120)
            if r.status_code == 400:
                return None
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError:
            if attempt == 5:
                raise
            time.sleep(3 * (attempt + 1))


def needs(acf: dict) -> list[str]:
    """Target languages whose article or title is missing / wrong."""
    return [l for l in CF if l != SOURCE and (content_needs_work(acf.get(CF[l]) or "", l)
                                               or title_needs_work(acf.get(TF[l]) or "", l))]


def source_ok(acf: dict) -> str | None:
    html = acf.get(CF[SOURCE]) or ""
    if len(visible(html)) < MIN_CHARS:
        return "no English article"
    p = content_problem(html, SOURCE)
    return None if p in (None, "token leak") else f"English article looks wrong: {p}"


def live_temples():
    if TEMPLE:
        yield get(f"{API}/{TEMPLE}", context="edit", _fields="id,slug,title,acf")
        return
    page = 1
    while True:
        batch = get(API, per_page=50, page=page, context="edit", orderby="id", order="asc", _fields="id,slug,title,acf")
        if not batch:
            return
        yield from batch
        print(f"  scanned page {page}", flush=True)
        page += 1


def fmt(s):
    m, s = divmod(int(s), 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def log(row):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    t0 = time.time()
    print("DRY RUN -- nothing translated or written\n" if not GO else f"LIVE RUN -- writing to {settings.live_wp_url}\n", flush=True)
    work, refused = [], []
    for t in live_temples():
        acf = t.get("acf") or {}
        todo = needs(acf)
        if not todo:
            continue
        why = source_ok(acf)
        if why:
            refused.append((t["id"], t["slug"], why))
            continue
        if ONLY and len(work) >= ONLY:
            break
        work.append((t, todo))
    print(f"\nscan took {fmt(time.time() - t0)}: {len(work)} temples to translate"
          + (f", {len(refused)} refused (bad or missing English source)" if refused else ""), flush=True)
    for r in refused:
        print("  refused:", r)
    if not GO:
        for i, (t, todo) in enumerate(work, 1):
            print(f"[{i}] {t['id']} {t['slug'][:50]}  needs: {','.join(todo)}")
        print("\nDry run only. Re-run with --go to translate.")
        return

    t1 = time.time()
    ok = failed = 0
    for i, (t, todo) in enumerate(work, 1):
        if BUDGET and spent() >= BUDGET:
            print(f"\nBUDGET REACHED (Rs{spent():.0f}): stopping. Re-run to continue.", flush=True)
            break
        start, msgs, err = time.time(), [], None
        try:
            pipe.process_temple(t["id"], operation="translate", source=SOURCE, log=msgs.append)
        except Exception as e:  # noqa: BLE001 -- one temple must not stop the run...
            err = e
        # ...but running out of credit must: every later temple would fail the same way.
        text = " ".join(msgs) + " " + str(err or "")
        if "402" in text or "Payment Required" in text or "insufficient" in text.lower():
            print(f"\n[{i}/{len(work)}] {t['slug'][:40]}  PROVIDER OUT OF CREDIT -- stopping. Top up and re-run.", flush=True)
            log({"temple": t["id"], "slug": t["slug"], "result": "stopped: out of credit"})
            break
        # Trust but verify: read the temple back from live and re-check every language.
        after = get(f"{API}/{t['id']}", context="edit", _fields="acf") or {}
        still = needs(after.get("acf") or {})
        fixed = len(todo) - len([l for l in todo if l in still])
        if not still:
            ok += 1
            status = f"verified {len(todo)}/{len(todo)}"
        else:
            failed += 1
            status = f"verified {fixed}/{len(todo)}; still missing {','.join(still)}" + (f" ({str(err)[:60]})" if err else "")
        log({"temple": t["id"], "slug": t["slug"], "needed": todo, "still_missing": still, "error": str(err) if err else None,
             "seconds": round(time.time() - start)})
        el = time.time() - t1
        print(f"[{i}/{len(work)}] {time.strftime('%H:%M:%S')} elapsed {fmt(el)} eta {fmt(el / i * (len(work) - i))}  "
              f"spent Rs{spent():.1f}  {t['slug'][:36]}  {status} in {time.time() - start:.0f}s", flush=True)
    print(f"\nDONE in {fmt(time.time() - t0)}: {ok} temples fully verified, {failed} incomplete (re-run to retry them). "
          f"Gemini spend Rs{spent():.2f} over {_spend['calls']} calls. Details: {LOG}")


if __name__ == "__main__":
    main()
