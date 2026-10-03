"""
Run the FULL pipeline for one temple by ID:

    pull content from WordPress
      -> detect source language (or use the one you pass)
      -> translate every OTHER language (structure-preserving, Gemini)
      -> generate audio (Sarvam)
      -> write content + titles + audio back to WordPress

Then just open the temple on the staging site to see it.

Usage:
    python run_temple.py <temple_id>            # auto-detect source (mr > en > hi)
    python run_temple.py <temple_id> en         # force English as the source
    python run_temple.py <temple_id> en mr,hi   # force source + only these targets

Needs in .env:  WP_URL, WP_USER, WP_APP_PASSWORD, SARVAM_API_KEY,
                and Gemini (GEMINI_USE_ADC + GCP_PROJECT, or GEMINI_API_KEY).
"""

import logging
import sys

import httpx

from app.config import settings
from app.tasks import wp_client as wp
from app.tasks.gemini_translate import translate as gtranslate
from app.tasks.source_detect import detect_source_language
from app.tasks import costs
from app.tasks.field_checks import script_frac
from app.tasks.safe_translate import translate_article, translate_title
from app.tasks.structured_translate import strip_cosmetic_spans, strip_tags

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("run_temple")



def _fetch_post(post_id: int) -> dict:
    url = settings.wp_url.rstrip("/") + f"/wp-json/wp/v2/temple/{post_id}"
    r = httpx.get(url, params={"context": "edit"},
                  auth=(settings.wp_user, settings.wp_app_password), timeout=30)
    r.raise_for_status()
    return r.json()


def run(post_id: int, forced_source: str | None = None, targets: list[str] | None = None) -> None:
    if not (settings.wp_url and settings.wp_user and settings.wp_app_password):
        log.error("WP creds missing — set WP_URL, WP_USER, WP_APP_PASSWORD in .env.")
        return

    costs.set_temple(post_id)  # log this run's Gemini/Sarvam spend against the temple

    # Pick up any language added via the dashboard's /languages registry since
    # the last refresh, so its ACF field keys are known before we need them.
    wp.refresh_language_fields()

    post = _fetch_post(post_id)
    acf = post.get("acf", {}) or {}
    if not acf:
        log.error("No 'acf' block on this post. ACF fields must be exposed to REST (context=edit).")
        return

    slug = post.get("slug", f"temple-{post_id}")
    # Strip the per-word cosmetic <span> wrappers up front: cleaner stored HTML,
    # full-sentence translation context, and ~1-2 API calls instead of ~600.
    content = {lang: strip_cosmetic_spans(acf.get(field) or "") for lang, field in wp.CONTENT_FIELD_KEYS.items()}
    titles = {lang: (acf.get(field) or "") for lang, field in wp.TITLE_FIELD_KEYS.items()}

    source = forced_source or detect_source_language(content, candidates=("mr", "en", "hi")).source
    if not source or not content.get(source, "").strip():
        log.error("No usable source content (source=%r). Pass a source lang explicitly, e.g. "
                  "`python run_temple.py %s en`.", source, post_id)
        return

    src_title = strip_tags(titles.get(source) or post.get("title", {}).get("rendered", ""))
    # Titles come from the English title where there is one (see safe_translate).
    wp_title = strip_tags(post.get("title", {}).get("raw") or post.get("title", {}).get("rendered", ""))
    en_title = next((t for t in (strip_tags(titles.get("en") or ""), wp_title) if t and script_frac(t, "en") >= 0.85), "")
    title_candidates = [("en", en_title), (source, src_title)]
    tgts = targets or [l for l in wp.CONTENT_FIELD_KEYS if l != source]
    log.info("Temple %s (slug=%s): source=%s (%d chars) -> targets=%s",
             post_id, slug, source, len(content[source]), ",".join(tgts))

    for tgt in tgts:
        if tgt == source:
            continue
        try:
            log.info("[%s] translating title + content (Gemini)...", tgt)
            # Validated: raises BadTranslation (nothing saved, no audio bought) if Gemini
            # keeps returning the source text instead of a translation.
            html = translate_article(content[source], source, tgt, gtranslate)
            title = (en_title if tgt == "en" else translate_title(title_candidates, tgt, gtranslate)) or ""
            if not title:
                log.warning("[%s] title could not be translated safely - left as it was", tgt)
            wp.write_title_and_content(post_id, tgt, title, html)
            log.info("[%s] wrote %d chars; generating + uploading audio (Sarvam)...", tgt, len(html))
            wp.generate_and_save(strip_tags(html), tgt, post_id, slug)
            log.info("[%s] DONE", tgt)
        except Exception as e:
            log.error("[%s] FAILED: %s", tgt, e)

    # Audio for the source language too, so every language has a Listen button.
    try:
        log.info("[%s] generating source-language audio...", source)
        wp.generate_and_save(strip_tags(content[source]), source, post_id, slug)
    except Exception as e:
        log.error("[%s] source audio FAILED: %s", source, e)

    log.info("All done for temple %s — open the staging page to check it.", post_id)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_temple.py <temple_id> [source_lang] [targets_csv]")
        raise SystemExit(1)
    pid = int(sys.argv[1])
    src = sys.argv[2] if len(sys.argv) > 2 else None
    tg = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    run(pid, src, tg)
