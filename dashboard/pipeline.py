"""
Per-temple processing for the dashboard — the same flow as run_temple.py but
parameterized by operation (translate / audio / full) + selected languages, and
with a log callback so the worker can stream progress to a job.
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.tasks import wp_client as wp
from app.tasks.gemini_translate import translate as gtranslate
from app.tasks.source_detect import detect_source_language, visible_text_length
from app.tasks.structured_translate import strip_cosmetic_spans, strip_tags, translate_html

WP_BASE = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
AUTH = (settings.wp_user, settings.wp_app_password)
ALL_LANGS = ("mr", "en", "hi", "gj", "ta", "te", "ml", "kn")
GEMINI_MAX = 6000
MIN_CHARS = 200


def _fetch(post_id: int) -> dict:
    r = httpx.get(f"{WP_BASE}/temple/{post_id}", params={"context": "edit"}, auth=AUTH, timeout=45)
    r.raise_for_status()
    return r.json()


def process_temple(post_id, operation="full", languages=None, source=None, log=print,
                   translate_langs=None, audio_langs=None):
    """
    Two ways to call:
      • batch mode  — operation ('translate'|'audio'|'full') + languages list.
      • granular    — explicit translate_langs + audio_langs (per-language choice).
    If translate_langs/audio_langs are given, they win. Source is never translated.
    """
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
        selected = list(languages or ALL_LANGS)
        to_translate = [l for l in selected if l != src] if operation in ("translate", "full") else []
        to_audio = (selected if languages else [src] + [l for l in selected if l != src]) \
            if operation in ("audio", "full") else []

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
            futs = {ex.submit(_translate_one, t): t for t in to_translate}
            for fut in as_completed(futs):
                tgt = futs[fut]
                try:
                    _, title, html = fut.result()
                    results[tgt] = (title, html)
                    log(f"[{tgt}] translated ({len(html)} chars)")
                except Exception as e:  # one language failing shouldn't kill the rest
                    log(f"[{tgt}] TRANSLATE FAILED: {e}")
        for tgt in to_translate:  # write back sequentially (avoid racing ACF writes)
            if tgt in results:
                title, html = results[tgt]
                wp.write_title_and_content(post_id, tgt, title, html)
                content[tgt] = html
        log(f"wrote {len(results)}/{len(to_translate)} language(s) to WordPress")

    # --- audio (uses freshly-translated content where available) ---
    for lang in to_audio:
        text = content.get(lang, "")
        if visible_text_length(text) < MIN_CHARS:
            log(f"[{lang}] no content — skipping audio")
            continue
        log(f"[{lang}] generating audio…")
        wp.generate_and_save(strip_tags(text), lang, post_id, slug)
        log(f"[{lang}] audio done")

    log("✓ complete")
