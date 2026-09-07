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
TRANSLATE_WORKERS = settings.translate_workers  # languages translated at once (.env: TRANSLATE_WORKERS)
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


class Cancelled(RuntimeError):
    """Raised when a job is asked to stop. Never raised in the middle of a
    paid step: translations Gemini has already charged for are written to
    WordPress first, so stopping costs progress but never money."""


def process_temple(post_id, operation="full", languages=None, source=None, log=print,
                   translate_langs=None, audio_langs=None, force=False,
                   should_cancel=None):
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
        _process(post_id, operation, languages, source, log, translate_langs,
                 audio_langs, force, should_cancel)
    finally:
        costs.set_temple(None)


def _process(post_id, operation, languages, source, log, translate_langs, audio_langs,
             force, should_cancel=None):
    # Pick up any language added via the dashboard's /languages registry since
    # the last refresh, so its ACF field keys are known before we need them.
    wp.refresh_language_fields()

    def _stop_if_asked(stage: str) -> None:
        if should_cancel and should_cancel():
            raise Cancelled(stage)

    _stop_if_asked("before starting")
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
        # One worker per language: capped at 8 this used to leave the 9th
        # (usually pa) queued behind the others, adding ~10s of pure wait
        # to every temple. Gemini is billed per call, not per second, so
        # width costs nothing; TRANSLATE_WORKERS caps it if Gemini 429s.
        with ThreadPoolExecutor(max_workers=min(len(to_translate), TRANSLATE_WORKERS)) as ex:
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
        # Write-back is one request for all languages, with a per-language
        # fallback: the staging host can take 45s+ under load, and a single
        # timeout must never throw away translations Gemini already charged for.
        written = []
        ready = {t: results[t] for t in to_translate if t in results}
        # One request for every language: WordPress charges its overhead per
        # request, not per field (measured 65.5s -> 2.9s for 9 languages).
        if ready:
            try:
                wp.write_all_translations(post_id, ready)
                written = list(ready)
                for tgt in written:
                    content[tgt] = ready[tgt][1]
            except Exception as e:  # noqa: BLE001 -- batch is all-or-nothing
                log(f"batched write failed ({e}); retrying one language at a time")
        # Fallback: the batch is all-or-nothing, so on failure go back to the
        # slow path, which saves whatever it can rather than losing everything.
        if ready and not written:
            for tgt in to_translate:
                if tgt in results:
                    title, html = results[tgt]
                    try:
                        wp.write_title_and_content(post_id, tgt, title, html)
                        content[tgt] = html
                        written.append(tgt)
                    except Exception as e:  # noqa: BLE001 -- keep the other languages
                        log(f"[{tgt}] WRITE FAILED (translation kept, not saved): {e}")
        log(f"wrote {len(written)}/{len(to_translate)} language(s) to WordPress")
        # Wrote nothing at all -> the job must FAIL, not report success. 151
        # temples were marked "done" with 0/9 written when Gemini's prepaid
        # credits ran out: every language 429'd, the loop completed, and the
        # queue marched on reporting success. A temple that produced nothing
        # has to be visibly broken so it can be re-queued.
        # Partial counts as broken too: when the prepaid balance hovers at zero,
        # per-language calls are authorised independently, so one temple can end
        # up 6/9 written and still look finished. The languages that did write
        # are already saved, and a re-run only fills the gaps (the "already has
        # content" guard above), so failing here loses nothing and keeps the
        # shortfall visible instead of silently shipping a half-done temple.
        if len(written) < len(to_translate):
            raise RuntimeError(
                f"only {len(written)}/{len(to_translate)} languages written "
                f"({','.join(l for l in to_translate if l not in written)} missing) - "
                "check the translation provider's credits/quota"
            )

    # Stop here if asked: translation is written, so nothing paid for is lost,
    # and audio (the expensive half) has not started.
    _stop_if_asked("after translation, before audio")

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
            # Checked per language: audio is the expensive half, so a stop
            # request must not have to wait for all 10 to finish. Whatever is
            # already uploaded stays -- only the unstarted ones are skipped.
            _stop_if_asked(f"before {lang} audio")
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
