"""
Per-temple processing for the dashboard — the same flow as run_temple.py but
parameterized by operation (translate / audio / full) + selected languages, and
with a log callback so the worker can stream progress to a job.
"""

from __future__ import annotations

import httpx
from contextvars import copy_context
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.tasks import costs
from app.tasks import wp_client as wp
from app.tasks.gemini_translate import translate as gtranslate
from app.tasks.source_detect import detect_source_language, visible_text_length
from app.tasks.structured_translate import strip_cosmetic_spans, strip_tags, translate_html

WP_BASE = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
AUTH = (settings.wp_user, settings.wp_app_password)
GEMINI_MAX = 6000
AUDIO_WORKERS = settings.audio_workers   # languages voiced at once (.env: AUDIO_WORKERS)
MIN_CHARS = 200


# The 10web staging host drops connections under load (WinError 10054), and this
# is the first call of every job -- without a retry a blip fails the whole temple
# before any work starts. Gemini and Sarvam already retry; WordPress did not.
@retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, min=2, max=20),
       retry=retry_if_exception_type(httpx.HTTPError), reraise=True)
def _fetch(post_id: int) -> dict:
    r = httpx.get(f"{WP_BASE}/temple/{post_id}", params={"context": "edit"}, auth=AUTH, timeout=60)
    r.raise_for_status()
    return r.json()


def process_temple(post_id, operation="full", languages=None, source=None, log=print,
                   translate_langs=None, audio_langs=None, force=False):
    """
    Two ways to call:
      • batch mode  — operation ('translate'|'audio'|'full') + languages list.
      • granular    — explicit translate_langs + audio_langs (per-language choice).
    If translate_langs/audio_langs are given, they win. Source is never translated.

    force=True deliberately overrides the "don't overwrite existing content"
    guard below -- use it to intentionally regenerate a translation that's
    already there (e.g. fixing a bad one). Off by default: a checked language
    that already has content is normally left untouched.
    """
    # Attribute every Gemini/Sarvam charge from here on to this temple, so the
    # CSV export can total it. Cleared in the finally below.
    costs.set_temple(post_id)
    try:
        _process(post_id, operation, languages, source, log, translate_langs, audio_langs, force)
    finally:
        costs.set_temple(None)


def _process(post_id, operation, languages, source, log, translate_langs, audio_langs, force):
    # Pick up any language added via the dashboard's /languages registry since
    # the last refresh, so its ACF field keys are known before we need them.
    wp.refresh_language_fields()

    post = _fetch(post_id)
    acf = post.get("acf") or {}
    slug = post.get("slug", f"temple-{post_id}")
    content = {l: strip_cosmetic_spans(acf.get(f) or "") for l, f in wp.CONTENT_FIELD_KEYS.items()}
    titles = {l: (acf.get(f) or "") for l, f in wp.TITLE_FIELD_KEYS.items()}

    src = source or detect_source_language(content, candidates=("mr", "en", "hi")).source
    if not src or visible_text_length(content.get(src, "")) < MIN_CHARS:
        raise RuntimeError(f"No usable source content (source={src!r})")
    src_title = strip_tags(titles.get(src) or post.get("title", {}).get("rendered", ""))

    # Resolve what to translate and what to voice.
    if translate_langs is not None or audio_langs is not None:
        to_translate = [l for l in (translate_langs or []) if l != src]
        to_audio = list(audio_langs or [])
    else:
        selected = list(languages or wp.CONTENT_FIELD_KEYS)
        to_translate = [l for l in selected if l != src] if operation in ("translate", "full") else []
        to_audio = (selected if languages else [src] + [l for l in selected if l != src]) \
            if operation in ("audio", "full") else []

    # Never overwrite a language that already has real content -- whether it
    # got there from an earlier pipeline run or was authored independently
    # (e.g. English/Hindi on temples where those were hand-written, not
    # translated from the Marathi source). Only fill in what's actually
    # empty; audio is unaffected by this and still runs for every requested
    # language, using whatever content -- old or newly translated -- ends up
    # in place. force=True deliberately skips this guard.
    if force:
        log("force=True — translating every selected language, including ones with existing content")
    else:
        already_filled = [t for t in to_translate if visible_text_length(content.get(t, "")) >= MIN_CHARS]
        to_translate = [t for t in to_translate if t not in already_filled]
        if already_filled:
            log(f"already has content, not overwriting: {','.join(already_filled)}")

    log(f"source={src} · translate={','.join(to_translate) or '-'} · audio={','.join(to_audio) or '-'}")

    # --- translate (parallel) ---
    if to_translate:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _translate_one(tgt):
            title = gtranslate(src_title, src, tgt) if src_title.strip() else ""
            html = translate_html(content[src], src, tgt, gtranslate, max_chars=GEMINI_MAX)
            return tgt, title, html

        results = {}
        log(f"translating {len(to_translate)} language(s) in parallel…")
        with ThreadPoolExecutor(max_workers=min(len(to_translate), 8)) as ex:
            # copy_context: costs.set_temple lives in a ContextVar, and a pool
            # thread starts with an empty context unless we carry ours in.
            futs = {ex.submit(copy_context().run, _translate_one, t): t for t in to_translate}
            for fut in as_completed(futs):
                tgt = futs[fut]
                try:
                    _, title, html = fut.result()
                    results[tgt] = (title, html)
                    log(f"[{tgt}] translated ({len(html)} chars)")
                except Exception as e:  # one language failing shouldn't kill the rest
                    log(f"[{tgt}] TRANSLATE FAILED: {e}")
        # Written back sequentially (avoid racing ACF writes), and each language
        # guarded on its own: the staging host can take 45s+ under load, and a
        # single timeout used to raise out of this loop and throw away every
        # remaining translation -- work Gemini had already charged for.
        written = []
        for tgt in to_translate:  # write back sequentially (avoid racing ACF writes)
            if tgt in results:
                title, html = results[tgt]
                try:
                    wp.write_title_and_content(post_id, tgt, title, html)
                    content[tgt] = html
                    written.append(tgt)
                except Exception as e:  # noqa: BLE001 -- keep the other languages
                    log(f"[{tgt}] WRITE FAILED (translation kept, not saved): {e}")
        log(f"wrote {len(written)}/{len(to_translate)} language(s) to WordPress")

    # --- audio (uses freshly-translated content where available) ---
    # Same "don't redo work that's already there" principle as translate:
    # a language that already has an audio file is skipped by default (saves
    # a real Sarvam charge every time), unless force=True.
    audio_present = {l: bool(acf.get(f)) for l, f in wp.AUDIO_FIELD_KEYS.items()}
    todo = []
    for lang in to_audio:
        text = content.get(lang, "")
        if visible_text_length(text) < MIN_CHARS:
            log(f"[{lang}] no content — skipping audio")
            continue
        if audio_present.get(lang) and not force:
            log(f"[{lang}] audio already exists — not regenerating (use Force to redo it)")
            continue
        todo.append(lang)

    # Languages are voiced concurrently -- audio was the sequential half of the
    # job and each language is independent. AUDIO_WORKERS is deliberately below
    # the number of languages: every worker streams chunk after chunk at Sarvam,
    # and a 429 storm costs real money for half-synthesised audio.
    if todo:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def _audio_one(lang):
            wp.generate_and_save(strip_tags(content[lang]), lang, post_id, slug)

        log(f"generating audio for {len(todo)} language(s), {AUDIO_WORKERS} at a time…")
        with ThreadPoolExecutor(max_workers=min(len(todo), AUDIO_WORKERS)) as ex:
            futs = {ex.submit(copy_context().run, _audio_one, l): l for l in todo}
            for fut in as_completed(futs):
                lang = futs[fut]
                try:
                    fut.result()
                    log(f"[{lang}] audio done")
                except Exception as e:  # one language failing shouldn't kill the rest
                    log(f"[{lang}] AUDIO FAILED: {e}")

    log("✓ complete")
