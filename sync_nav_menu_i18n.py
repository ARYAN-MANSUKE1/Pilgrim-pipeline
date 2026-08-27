"""
Add every missing language to the site's WordPress nav menu items (main nav +
footer legal links), matching the theme's existing per-item pattern exactly:

    <div class="mr_lang dis_lang" style="display: block;">...</div>
    <div class="en_lang dis_lang" style="display: none;">...</div>
    ...

toggleLanguage() in functions.php already shows/hides ANY element whose class
matches "<lang>_lang" -- so once a menu item's title HTML contains a language's
div, that language works immediately, with no further code/theme changes.

Menu items are a REST-writable post type (nav_menu_item), so this translates
each item's English text into every language it's missing and PATCHes it back
in one pass -- no manual Elementor/Appearance > Menus editing needed.

Run:  python sync_nav_menu_i18n.py
"""

import re
import sys

import httpx

from app.config import LANGUAGE_NAMES, settings
from app.tasks.gemini_translate import translate as gtranslate

WP_BASE = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
AUTH = (settings.wp_user, settings.wp_app_password)

ALL_LANGS = ("mr", "en", "hi", "gj", "ta", "te", "ml", "kn", "bn", "pa")
SOURCE_LANG = "en"  # translate FROM the existing English div (cleanest, unambiguous)

_DIV_RE = re.compile(r'<div class="(\w+)_lang dis_lang"[^>]*>(.*?)</div>', re.S)


def _existing_langs_and_text(title_html: str) -> dict[str, str]:
    return {m.group(1): m.group(2).strip() for m in _DIV_RE.finditer(title_html)}


def _build_div(lang: str, text: str) -> str:
    return f'<div class="{lang}_lang dis_lang" style="display: none;">{text}</div>'


def sync_item(item_id: int) -> None:
    r = httpx.get(f"{WP_BASE}/menu-items/{item_id}", params={"context": "edit"}, auth=AUTH, timeout=30)
    r.raise_for_status()
    title = r.json()["title"]["raw"]

    have = _existing_langs_and_text(title)
    source_text = have.get(SOURCE_LANG)
    if not source_text:
        print(f"[{item_id}] SKIP -- no '{SOURCE_LANG}_lang' div to translate from")
        return

    missing = [l for l in ALL_LANGS if l not in have and l != SOURCE_LANG]
    if not missing:
        print(f"[{item_id}] already has every language -- skipping")
        return

    new_title = title
    added = []
    for lang in missing:
        try:
            text = gtranslate(source_text, SOURCE_LANG, lang).strip()
        except Exception as e:
            print(f"[{item_id}] {lang}: TRANSLATE FAILED -- {e}")
            continue
        new_title += _build_div(lang, text)
        added.append(lang)

    if not added:
        print(f"[{item_id}] nothing added (all translations failed)")
        return

    resp = httpx.post(f"{WP_BASE}/menu-items/{item_id}", json={"title": new_title}, auth=AUTH, timeout=30)
    resp.raise_for_status()
    print(f"[{item_id}] '{source_text}' -> added {', '.join(added)}")


def main():
    r = httpx.get(f"{WP_BASE}/menu-items", params={"per_page": 50, "context": "edit"}, auth=AUTH, timeout=30)
    r.raise_for_status()
    ids = [it["id"] for it in r.json()]
    print(f"Found {len(ids)} menu items. Syncing missing languages ({', '.join(l for l in ALL_LANGS if l != SOURCE_LANG)})...\n")
    for item_id in ids:
        sync_item(item_id)
    print("\nDone. Reload the site and switch languages to verify.")


if __name__ == "__main__":
    if not (settings.wp_url and settings.wp_user and settings.wp_app_password):
        sys.exit("WP credentials missing in .env")
    main()
