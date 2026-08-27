"""
Single-temple full pipeline: translate missing languages → generate audio.

1. Fetches all language content fields from WordPress
2. Translates any empty languages from Marathi using Gemini (Engineer 1's approach)
3. Generates Sarvam TTS audio for every language that has content
4. Uploads audio + sets ACF audio fields on WordPress

Requires GEMINI_API_KEY in .env for translation step.

Usage:
    python demo_temple.py <temple_id>

Example:
    python demo_temple.py 11024
"""

import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("demo")

from app.tasks.wp_client import (
    fetch_temple_meta,
    fetch_all_content,
    translate_with_gemini,
    write_title_and_content,
    generate_and_save,
    strip_html,
    LANG_NAMES,
)

LANGS = ["mr", "hi", "en", "gj", "ta", "te"]

# Fields with fewer than this many characters are treated as placeholders
# ("coming soon", "जल्द आ रहा है", etc.) and skipped for translation and audio.
MIN_CONTENT_CHARS = 150

# Preference order when picking a source language for translation
SOURCE_PRIORITY = ["mr", "en", "hi", "gj", "ta", "te"]


def has_real_content(text: str) -> bool:
    return len(text.strip()) >= MIN_CONTENT_CHARS


def find_source(plain_cache: dict) -> tuple[str, str] | None:
    """Return (lang_code, plain_text) of the best available source, or None."""
    for lang in SOURCE_PRIORITY:
        plain = plain_cache.get(lang, "")
        if has_real_content(plain):
            return lang, plain
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    temple_id = int(sys.argv[1])

    # ── 1. Fetch temple meta + all content fields ─────────────────────────
    logger.info("Looking up temple %d...", temple_id)
    meta = fetch_temple_meta(temple_id)
    temple_slug = meta["slug"]
    logger.info("Temple: %s  (slug: %s)", meta["title"], temple_slug)

    logger.info("Checking content fields...")
    content = fetch_all_content(temple_id)          # {lang: raw_html}
    plain   = {lang: strip_html(html) for lang, html in content.items()}

    print("\n── Content status ──────────────────────────────")
    for lang, text in plain.items():
        if not text:
            status = "EMPTY"
        elif not has_real_content(text):
            status = f"PLACEHOLDER ({len(text)} chars — skipped)"
        else:
            status = f"{len(text)} chars"
        print(f"  {lang:3s}  {status}")
    print()

    source = find_source(plain)
    if not source:
        logger.error("No language has real content (≥%d chars) — nothing to translate from.", MIN_CONTENT_CHARS)
        sys.exit(1)

    src_lang, src_text = source
    src_html  = content[src_lang]   # raw HTML — sent to Gemini so structure is preserved
    src_title = meta["marathi_title"] if src_lang == "mr" else plain[src_lang].split("\n")[0][:100]
    logger.info("Using %s as translation source (%d chars).", LANG_NAMES[src_lang], len(src_text))

    # ── 2. Translate any empty language using Gemini ──────────────────────
    print("── Translation (Gemini) ────────────────────────")
    for lang in LANGS:
        if lang == src_lang:
            continue
        if has_real_content(plain.get(lang, "")):
            logger.info("%s: already has real content — skipping.", LANG_NAMES[lang])
            continue
        logger.info("Translating %s → %s...", LANG_NAMES[src_lang], LANG_NAMES[lang])
        try:
            result = translate_with_gemini(src_title, src_html, lang, source_lang=src_lang)
            translated_html = result.get("content", "")
            if not has_real_content(strip_html(translated_html)):
                logger.warning("  %s: Gemini returned short/empty content — skipping write.", LANG_NAMES[lang])
                continue
            write_title_and_content(temple_id, lang, result["title"], translated_html)
            content[lang] = translated_html
            plain[lang]   = strip_html(translated_html)
            logger.info("  %s done (%d chars).", LANG_NAMES[lang], len(result["content"]))
            time.sleep(8)  # stay under Gemini free-tier rate limit (15 req/min)
        except Exception as e:
            logger.warning("  %s translation failed — skipping. %s", LANG_NAMES[lang], e)
    print()

    # ── 3. Generate audio for every language that now has real content ─────
    print("── Audio generation (Sarvam) ───────────────────")
    results = {}
    for lang in LANGS:
        plain_text = plain.get(lang, "")
        if not has_real_content(plain_text):
            results[lang] = "skipped (no content)" if not plain_text else "skipped (placeholder)"
            continue
        logger.info("Generating %s audio (%d chars)...", LANG_NAMES[lang], len(plain_text))
        try:
            attachment_id = generate_and_save(plain_text, lang, temple_id, temple_slug)
            results[lang] = f"attachment {attachment_id}" if attachment_id else "generated locally"
        except Exception as e:
            logger.error("%s audio failed: %s", LANG_NAMES[lang], e)
            results[lang] = f"ERROR: {e}"
    print()

    # ── 4. Summary ────────────────────────────────────────────────────────
    print("── Summary ─────────────────────────────────────")
    for lang, result in results.items():
        print(f"  {LANG_NAMES[lang]:10s}  {result}")
    print()


if __name__ == "__main__":
    main()
