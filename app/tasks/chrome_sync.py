"""
Translate + push the footer/header chrome strings for several languages at
once, in parallel -- matching how the pipeline already parallelizes temple
translation (ThreadPoolExecutor), instead of one language at a time.

The earlier sequential version took ~10-15 minutes for 9 languages x 12
strings (~108 calls, one after another). Running the languages concurrently
cuts that to roughly the time of the single slowest language.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.tasks.push_ui_i18n import push_ui_strings
from app.tasks.ui_strings import translate_ui_strings


def sync_chrome_parallel(langs: list[str]) -> list[str]:
    log: list[str] = []

    def _one(lang: str):
        strings = translate_ui_strings(lang)
        result = push_ui_strings(lang, strings)
        return lang, result.get("keys_saved")

    with ThreadPoolExecutor(max_workers=min(len(langs), 8)) as ex:
        futures = {ex.submit(_one, lang): lang for lang in langs}
        for fut in as_completed(futures):
            lang = futures[fut]
            try:
                done_lang, n = fut.result()
                log.append(f"[chrome/{done_lang}] saved {n} keys")
            except Exception as e:
                log.append(f"[chrome/{lang}] FAILED: {e}")
    return log
