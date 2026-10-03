"""
Repair translation fields that are in the wrong language / have the batching
marker leaked into them / have a wrong-script title -- on LIVE and STAGING.

Fix modes (--fix a,b,c). The default is only the free / near-free ones:
    copy      live field is bad but the same field on staging is fine -> copy it (free)
    junk      only problem is the leaked marker zZqSEGqZz -> remove it (free)
    titles    wrong-script / empty title -> translate the title (a few rupees for all)
    articles  wrong-language article -> retranslate from English/Marathi/Hindi (COSTS Gemini money)
Each fix is checked with the same tests that flagged the field before it is written;
a field that fails its check is left untouched and logged.

Usage:
    python repair_fields.py                      # dry run: what each mode would do; nothing written
    python repair_fields.py --go                 # the free modes: copy, junk, titles
    python repair_fields.py --go --fix copy      # just one mode (or --fix copy,junk)
    python repair_fields.py --go --fix articles  # the paid part, when you are ready
    python repair_fields.py --go --only 10       # first 10 temples that need repair (test the path)
    python repair_fields.py --go --temple 1006   # one temple, by LIVE post id
    python repair_fields.py --go --workers 5     # more temples in parallel (default 3)

While running it prints one line per temple with the time, elapsed and an ETA.

Safe to re-run: fixed fields stop being flagged, so an interrupted run resumes.
Every field written or skipped is appended to repair_log.jsonl.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings
from app.tasks import costs, wp_client as wp
from app.tasks.field_checks import (MIN_CHARS, content_problem, mr_hi_duplicate, script_frac, strip_token,
                                    title_problem, visible)
from app.tasks.gemini_translate import translate as gtranslate
from app.tasks import sarvam_translate as sarvam
from app.tasks.safe_translate import BadTranslation, translate_article, translate_title

sys.stdout.reconfigure(encoding="utf-8")

GO = "--go" in sys.argv
ONLY = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None
TEMPLE = int(sys.argv[sys.argv.index("--temple") + 1]) if "--temple" in sys.argv else None
FIX = set(sys.argv[sys.argv.index("--fix") + 1].split(",")) if "--fix" in sys.argv else {"copy", "junk", "titles"}
if FIX - {"copy", "junk", "titles", "articles"}:
    sys.exit(f"--fix takes copy,junk,titles,articles (got {sorted(FIX)})")
# --engine sarvam translates with Sarvam's chat model (about Rs0.15-0.25 an article) instead of Gemini.
ENGINE = sys.argv[sys.argv.index("--engine") + 1] if "--engine" in sys.argv else "gemini"
if ENGINE not in ("gemini", "sarvam"):
    sys.exit(f"--engine takes gemini or sarvam (got {ENGINE!r})")
# --budget N stops the run once N rupees have been spent (in-flight temples finish first, so a few rupees
# of overshoot are possible). Defaults to Rs500 for Sarvam so it can never run away; no cap for Gemini.
BUDGET = float(sys.argv[sys.argv.index("--budget") + 1]) if "--budget" in sys.argv else (500.0 if ENGINE == "sarvam" else None)
TRANSLATE = sarvam.translate if ENGINE == "sarvam" else gtranslate
if ENGINE == "sarvam":
    sarvam.set_budget(BUDGET)
# Temples repaired at once (each also translates up to 6 languages in parallel).
# ponytail: 3 x 6 = 18 simultaneous Gemini calls; lower this if Gemini returns rate-limit errors.
WORKERS = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 3
LOG = "repair_log.jsonl"

LIVE = settings.live_wp_url.rstrip("/") + "/wp-json/wp/v2"
LIVE_AUTH = (settings.live_wp_user, settings.live_wp_app_password)
STAGE = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
STAGE_AUTH = (settings.wp_user, settings.wp_app_password)
LIVE_HOST = settings.live_wp_url.split("//")[-1].strip("/")
STAGE_HOST = settings.wp_url.split("//")[-1].strip("/")
SOURCE_ORDER = ["en", "mr", "hi"]
SHREDDED_SPANS = 200


_spend = {"in": 0, "out": 0, "calls": 0}
_spend_lock = threading.Lock()


def _track(usage: dict | None, lang: str = "") -> None:
    """Replaces costs.record_translation for this run: that one needs a per-thread
    temple id we don't set, and would silently drop every call made in our worker threads."""
    if not usage:
        return
    with _spend_lock:
        _spend["in"] += int(usage.get("promptTokenCount") or 0)
        # thinking tokens bill at the output rate, so they count as output
        _spend["out"] += int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0)
        _spend["calls"] += 1


costs.record_translation = _track


def spent_inr() -> float:
    if ENGINE == "sarvam":
        return sarvam.spent_inr()
    with _spend_lock:
        return costs.translation_inr(_spend["in"], _spend["out"])


def _transient(e: BaseException) -> bool:
    """Connection drops and 5xx retry; a 4xx (e.g. the 400 past the last page) is an answer, not a fault."""
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code >= 500
    return isinstance(e, httpx.HTTPError)


_net = retry(stop=stop_after_attempt(6), wait=wait_exponential(multiplier=2, min=3, max=60),
             retry=retry_if_exception(_transient), reraise=True)


@_net
def _get(url, auth, **kw):
    r = httpx.get(url, auth=auth, timeout=120, **kw)
    r.raise_for_status()
    return r


@_net
def _post(url, auth, **kw):
    # 120s, not 300: the host sometimes APPLIES a write and then never answers. Re-sending the
    # same fields is harmless, whereas a 300s timeout x 3 retries stalled a temple for 15-20 minutes
    # (seen 8 times in the last run) on a save that had already happened.
    r = httpx.post(url, auth=auth, timeout=120, **kw)
    r.raise_for_status()
    return r


def log(row: dict) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def find_bad(acf: dict) -> dict[str, str]:
    """{'content:ta': reason, 'title:kn': reason} for one temple's acf."""
    bad = {}
    for lang, f in wp.CONTENT_FIELD_KEYS.items():
        r = content_problem(acf.get(f) or "", lang)
        if not r and lang != "mr" and (acf.get(f) or "").count("<span") > SHREDDED_SPANS:
            # A translation made from a source with a <span> around every word comes out word by word
            # ("Of the state Important Among the temples Existing..."). It is in the right script, so
            # the checks above pass it. Genuine authored English tops out around 47 spans; these have
            # 567-1,059. (Marathi originals legitimately carry hundreds, hence the lang != "mr".)
            r = "word-by-word translation (per-word spans)"
        if r:
            bad[f"content:{lang}"] = r
    dup = mr_hi_duplicate(acf.get(wp.CONTENT_FIELD_KEYS["mr"]) or "", acf.get(wp.CONTENT_FIELD_KEYS["hi"]) or "")
    if dup:
        bad.setdefault(f"content:{dup}", "identical to the other of Marathi/Hindi")
    for lang, f in wp.TITLE_FIELD_KEYS.items():
        has = len(visible(acf.get(wp.CONTENT_FIELD_KEYS[lang]) or "")) >= MIN_CHARS
        r = title_problem(acf.get(f) or "", lang, has)
        if r:
            bad[f"title:{lang}"] = r
    return bad


def field_of(key: str) -> tuple[str, str, str]:
    kind, lang = key.split(":")
    return kind, lang, (wp.CONTENT_FIELD_KEYS if kind == "content" else wp.TITLE_FIELD_KEYS)[lang]


def clean_source(acf: dict, bad: dict) -> tuple[str, str] | None:
    for lang in SOURCE_ORDER:
        if f"content:{lang}" in bad:
            continue
        html = acf.get(wp.CONTENT_FIELD_KEYS[lang]) or ""
        if len(visible(html)) >= MIN_CHARS:
            return lang, strip_token(html)
    return None


def title_source(acf: dict, post_title: str, bad: dict) -> tuple[str, str] | None:
    en = (acf.get(wp.TITLE_FIELD_KEYS["en"]) or "").strip()
    if en and script_frac(en, "en") >= 0.85:
        return "en", en
    if post_title and script_frac(post_title, "en") >= 0.85:
        return "en", post_title
    mr = (acf.get(wp.TITLE_FIELD_KEYS["mr"]) or "").strip()
    if mr and "title:mr" not in bad:
        return "mr", mr
    return None


def field_is_fine(kind: str, lang: str, value: str) -> bool:
    if kind == "content":
        return len(visible(value)) >= MIN_CHARS and content_problem(value, lang) is None
    return bool(value.strip()) and title_problem(value, lang, True) is None


_write_lock = threading.Lock()


def fmt(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s" if h else f"{m}m{s:02d}s"


def repair_temple(t: dict, bad: dict) -> tuple[dict, list[str], int]:
    """Returns ({how: fields fixed}, fields that failed their check, fields left for another mode)."""
    acf = t["acf"]
    post_title = (t.get("title") or {}).get("raw", "")
    fixes: dict[str, tuple[str, str]] = {}   # key -> (new value, how)
    pending = list(bad)

    if "copy" in FIX and pending:
        stage = _get(f"{STAGE}/temple", STAGE_AUTH, params={"slug": t["slug"], "context": "edit",
                                                            "_fields": "id,acf"}).json()
        sacf = (stage[0].get("acf") or {}) if stage else {}
        for key in list(pending):
            kind, lang, field = field_of(key)
            sval = sacf.get(field) or ""
            if field_is_fine(kind, lang, sval):
                fixes[key] = (sval.replace(STAGE_HOST, LIVE_HOST), "copy")
                pending.remove(key)

    if "junk" in FIX:
        for key in list(pending):
            kind, lang, field = field_of(key)
            if kind == "content" and bad[key] == "token leak":
                cleaned = strip_token(acf.get(field) or "")
                if content_problem(cleaned, lang) is None:
                    fixes[key] = (cleaned, "junk")
                    pending.remove(key)

    todo = [k for k in pending if (k.startswith("title:") and "titles" in FIX)
            or (k.startswith("content:") and "articles" in FIX)]
    left = len(pending) - len(todo)
    csrc, tsrc = clean_source(acf, bad), title_source(acf, post_title, bad)

    def job(key: str):
        kind, lang, _ = field_of(key)
        if kind == "content":
            if not csrc or csrc[0] == lang:
                return key, None
            try:
                return key, translate_article(csrc[1], csrc[0], lang, TRANSLATE)
            except BadTranslation:
                return key, None
        return key, (translate_title([tsrc], lang, TRANSLATE) if tsrc else None)

    skipped: list[str] = []
    if todo:
        with ThreadPoolExecutor(max_workers=6) as ex:
            for key, value in ex.map(job, todo):
                if value is None:
                    skipped.append(field_of(key)[2])
                    log({"temple": t["id"], "slug": t["slug"], "field": field_of(key)[2], "was": bad[key],
                         "result": "SKIPPED (no clean source or failed checks)"})
                else:
                    fixes[key] = (value, "translated")

    live_up = {field_of(k)[2]: v for k, (v, how) in fixes.items()}
    # copy-fixes come FROM staging, so only the others need writing there too
    stage_up = {field_of(k)[2]: v.replace(LIVE_HOST, STAGE_HOST) for k, (v, how) in fixes.items() if how != "copy"}
    counts: dict[str, int] = {}
    for k, (v, how) in fixes.items():
        counts[how] = counts.get(how, 0) + 1
        log({"temple": t["id"], "slug": t["slug"], "field": field_of(k)[2], "was": bad[k], "result": f"fixed ({how})"})
    if live_up:
        # One write at a time: the hosts drop connections under concurrent load, and
        # translation (the slow part) has already happened outside this lock.
        with _write_lock:
            if stage_up:
                # Staging first: it is the pipeline's source of truth, and a later --force
                # migration would otherwise copy the bad text straight back to live.
                stage = _get(f"{STAGE}/temple", STAGE_AUTH, params={"slug": t["slug"], "_fields": "id"}).json()
                if stage:
                    _post(f"{STAGE}/temple/{stage[0]['id']}", STAGE_AUTH, json={"acf": stage_up})
            r = _post(f"{LIVE}/temple/{t['id']}", LIVE_AUTH, json={"acf": live_up}).json()
        dropped = [f for f in live_up if not (r.get("acf") or {}).get(f)]
        if dropped:
            counts["DROPPED-BY-WORDPRESS"] = len(dropped)
    return counts, skipped, left


def live_temples():
    if TEMPLE:
        yield _get(f"{LIVE}/temple/{TEMPLE}", LIVE_AUTH, params={"context": "edit", "_fields": "id,slug,title,acf"}).json()
        return
    page = 1
    while True:
        try:
            batch = _get(f"{LIVE}/temple", LIVE_AUTH, params={
                "per_page": 50, "page": page, "context": "edit", "orderby": "id", "order": "asc",
                "_fields": "id,slug,title,acf"}).json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:  # past the last page
                return
            raise
        if not batch:
            return
        yield from batch
        print(f"  scanned page {page} ({page * 50} temples so far)", flush=True)
        page += 1


def plan(work) -> dict[str, int]:
    """Dry-run estimate per mode, from live data alone (copy needs staging, so it is an upper bound)."""
    n = {"copy (upper bound, checked against staging at run time)": 0, "junk": 0, "titles": 0, "articles": 0}
    for t, bad in work:
        for key, reason in bad.items():
            kind, lang, field = field_of(key)
            n["copy (upper bound, checked against staging at run time)"] += 1
            if kind == "title":
                n["titles"] += 1
            elif reason == "token leak" and content_problem(strip_token(t["acf"].get(field) or ""), lang) is None:
                n["junk"] += 1
            else:
                n["articles"] += 1
    return n


def main() -> None:
    t0 = time.time()
    print("DRY RUN -- nothing will be translated or written\n" if not GO else
          f"LIVE RUN (fix: {','.join(sorted(FIX))}; translator: {ENGINE}"
          + (f", budget Rs{BUDGET:.0f}" if BUDGET else "")
          + f") -- {WORKERS} temples at a time, writing to live + staging\n", flush=True)
    work: list[tuple[dict, dict]] = []
    by_kind: dict[str, int] = {}
    for t in live_temples():
        bad = find_bad(t.get("acf") or {})
        if not bad:
            continue
        if ONLY and len(work) >= ONLY:
            break
        work.append((t, bad))
        for reason in bad.values():
            by_kind[reason.split(" (")[0]] = by_kind.get(reason.split(" (")[0], 0) + 1
    print(f"\nscan took {fmt(time.time() - t0)}: {len(work)} temples have at least one bad field\n"
          f"bad fields by problem: {by_kind}\n", flush=True)
    if not GO:
        print("what each mode would do:", plan(work))
        print("\nDry run only. Re-run with --go to fix (default: copy, junk, titles - all free/near-free).")
        return

    t1 = time.time()
    totals: dict[str, int] = {}
    skipped = failed = done = left_total = 0

    def run_one(item):
        t, bad = item
        start = time.time()
        return repair_temple(t, bad), time.time() - start

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(run_one, item): item for item in work}
        try:
            for fut in as_completed(futs):
                t, bad = futs[fut]
                done += 1
                try:
                    (counts, n_skipped, left), took = fut.result()
                    for k, v in counts.items():
                        totals[k] = totals.get(k, 0) + v
                    skipped += len(n_skipped)
                    left_total += left
                    status = (", ".join(f"{k} {v}" for k, v in counts.items()) or "nothing to change") \
                        + f" in {took:.0f}s" + (f", SKIPPED {n_skipped}" if n_skipped else "") \
                        + (f", left for later {left}" if left else "")
                except Exception as e:  # noqa: BLE001 -- one temple must not stop the run
                    failed += 1
                    status = f"FAILED {type(e).__name__}: {str(e)[:80]}"
                    log({"temple": t["id"], "slug": t["slug"], "result": status})
                if BUDGET and spent_inr() >= BUDGET:
                    print(f"\nBUDGET REACHED (Rs{spent_inr():.0f} of Rs{BUDGET:.0f}): stopping. Work already done is "
                          f"saved; re-run to continue.", flush=True)
                    for f in futs:
                        f.cancel()
                    break
                el = time.time() - t1
                print(f"[{done}/{len(work)}] {time.strftime('%H:%M:%S')} elapsed {fmt(el)} "
                      f"eta {fmt(el / done * (len(work) - done))}  spent Rs{spent_inr():.1f}  {t['slug'][:38]}  {status}",
                      flush=True)
        except KeyboardInterrupt:
            print("\nStopping: finishing the temples already in flight, then exiting...", flush=True)
            for f in futs:
                f.cancel()
    print(f"\nDONE in {fmt(time.time() - t0)}: fixed {totals or 'nothing'}; {skipped} skipped (failed their check); "
          f"{left_total} left for other modes; {failed} temples failed ({done}/{len(work)} processed). Details: {LOG}")
    u = sarvam.usage() if ENGINE == "sarvam" else {"calls": _spend["calls"], "in": _spend["in"], "out": _spend["out"]}
    if u["calls"]:
        n = totals.get("translated", 0)
        print(f"{ENGINE.upper()} SPEND: Rs{spent_inr():.2f} ({u['calls']} calls, {u['in']:,} tokens in, "
              f"{u['out']:,} out)" + (f"; average Rs{spent_inr() / n:.2f} per translated field" if n else ""))


if __name__ == "__main__":
    main()
