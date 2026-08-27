"""
End-to-end SAMPLE / DEMO (not the production pipeline).

Flow:  source HTML  -> translate to each language (GEMINI, structure-preserving)
                    -> print the translated HTML (images + paragraphs intact)
                    -> audio per language (SARVAM Bulbul v2)  [skipped if no Sarvam key]

Engines:  translation = Gemini (GEMINI_API_KEY)   |   audio = Sarvam (SARVAM_API_KEY)
Output goes to ./sample_output/.

Run:
    python sample.py                                  # English demo -> Marathi, Hindi
    python sample.py "<source html>" en mr            # your content, en -> mr
    python sample.py "<source html>" en mr,hi,gu,ta,te
"""

import logging
import os
import sys

from app.config import settings
from app.tasks.audio import synthesize
from app.tasks.gemini_translate import translate as gemini_translate
from app.tasks.structured_translate import strip_tags, translate_html

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("sample")

# A small but representative English source: heading, sub-heading, an inline image,
# a blank-line paragraph break, and a bullet list — the exact structure that used
# to collapse. Watch it survive in the translated output.
DEFAULT_TEXT = (
    "<h1><strong>Agasi Mata Swapna Mandir</strong></h1>\n"
    "<h3><strong>Dhuliya Road, Bardoli, Dist. Surat</strong></h3>\n"
    '<img class="alignleft wp-image-11028 size-full" src="https://x/4-1-7.jpg" alt="" width="1000" height="750" />'
    "The Agasi (Aghnashini) Mata temple in Bardoli is one of Gujarat's renowned "
    "temples, with a history spanning more than 400 years. Devotees believe that "
    "heartfelt prayers offered here are fulfilled.\n"
    "\n"
    "The temple is open for darshan from 6:00 am to 12:00 pm and again from 3:00 pm "
    "to 9:00 pm. Morning aarti is at 7:00 am and evening aarti at 7:00 pm.\n"
    "<h3><strong>Key Highlights</strong></h3>\n"
    "<ul>\n"
    " \t<li>Located 4 km from Bardoli and 39 km from Surat.</li>\n"
    " \t<li>Adequate parking facilities are available at the temple premises.</li>\n"
    " \t<li>Contact: Temple Office: 02622 220514</li>\n"
    "</ul>"
)


def run(source_text: str, source_lang: str, targets: list[str]) -> None:
    out_dir = "sample_output"
    os.makedirs(out_dir, exist_ok=True)

    do_audio = bool(settings.sarvam_api_key)
    if not do_audio:
        logger.warning("SARVAM_API_KEY not set — translation only, skipping audio.")

    for lang in targets:
        if lang == source_lang:
            continue
        logger.info("[%s] translating with Gemini...", lang)
        html = translate_html(source_text, source_lang, lang, gemini_translate)
        logger.info("[%s] translated HTML:\n%s\n", lang, html)

        # Save the translated HTML so you can eyeball structure (images/paragraphs).
        with open(os.path.join(out_dir, f"{lang}.html"), "w", encoding="utf-8") as fh:
            fh.write(html)

        if do_audio:
            logger.info("[%s] generating audio with Sarvam...", lang)
            data, ext = synthesize(strip_tags(html), lang)  # TTS gets plain text
            path = os.path.join(out_dir, f"{lang}.{ext}")
            with open(path, "wb") as fh:
                fh.write(data)
            logger.info("[%s] saved %s (%d bytes)\n", lang, path, len(data))

    logger.info("Done. Output (HTML%s) is in ./%s/", " + audio" if do_audio else "", out_dir)


if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TEXT
    src = sys.argv[2] if len(sys.argv) > 2 else "en"
    tgts = sys.argv[3].split(",") if len(sys.argv) > 3 else ["mr", "hi"]
    run(text, src, tgts)
