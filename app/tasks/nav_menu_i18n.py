"""
Keep the site's WordPress nav menu items (main nav + footer legal links) in
sync with the site's canonical language list -- automatically, on demand.

Each menu item's title HTML holds one <div class="{lang}_lang dis_lang"> block
per language; the theme's existing toggleLanguage() JS shows/hides whichever
block matches the selected language. This module ADDS a div (translated from
the English one, via Gemini) for every language the item is missing, and
REMOVES divs for languages no longer in the canonical list -- so adding or
retiring a language is a one-button operation, not a one-off script run by
hand after every migration or language change.

The canonical list is app.config.LANGUAGE_NAMES -- add/remove a language there
and call sync_nav_menu_items() to make the live menu match.
"""

from __future__ import annotations

import re

import httpx

from app.config import settings
from app.tasks.gemini_translate import translate as gtranslate

WP_BASE = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
AUTH = (settings.wp_user, settings.wp_app_password)

SOURCE_LANG = "en"  # translate FROM the existing English div (cleanest, unambiguous)

_DIV_RE = re.compile(r'<div class="(\w+)_lang dis_lang"[^>]*>(.*?)</div>', re.S)


def _parse_divs(title_html: str) -> dict[str, tuple[str, str]]:
    """lang -> (full_div_html, inner_text)."""
    out = {}
    for m in _DIV_RE.finditer(title_html):
        out[m.group(1)] = (m.group(0), m.group(2).strip())
    return out


def _build_div(lang: str, text: str, *, block: bool) -> str:
    display = "block" if block else "none"
    return f'<div class="{lang}_lang dis_lang" style="display: {display};">{text}</div>'


def _sync_one_item(item: dict, target_langs: list[str], log: list[str], default_block_lang: str) -> None:
    item_id = item["id"]
    title = item["title"]["raw"]
    divs = _parse_divs(title)

    source_text = (divs.get(SOURCE_LANG) or (None, None))[1]
    if not source_text:
        log.append(f"[{item_id}] skip -- no '{SOURCE_LANG}_lang' div to translate from")
        return

    changed = False

    # Remove languages no longer in the canonical list.
    for lang in list(divs):
        if lang not in target_langs:
            title = title.replace(divs[lang][0], "")
            changed = True

    # Add languages missing from this item.
    for lang in target_langs:
        if lang in divs:
            continue
        try:
            text = gtranslate(source_text, SOURCE_LANG, lang).strip()
        except Exception as e:
            log.append(f"[{item_id}] {lang}: translate failed -- {e}")
            continue
        title += _build_div(lang, text, block=(lang == default_block_lang))
        changed = True

    if not changed:
        log.append(f"[{item_id}] '{source_text}' already in sync")
        return

    resp = httpx.post(f"{WP_BASE}/menu-items/{item_id}", json={"title": title}, auth=AUTH, timeout=30)
    resp.raise_for_status()
    log.append(f"[{item_id}] '{source_text}' -> synced to {', '.join(target_langs)}")


def sync_nav_menu_items(target_langs: list[str], default_block_lang: str = "mr") -> list[str]:
    """
    Make every WordPress nav menu item match target_langs exactly: add a
    translated div for each missing language, remove divs for languages not
    in the list. Returns a log of what happened, one line per item.
    """
    log: list[str] = []
    r = httpx.get(f"{WP_BASE}/menu-items", params={"per_page": 50, "context": "edit"}, auth=AUTH, timeout=30)
    r.raise_for_status()
    items = r.json()
    log.append(f"Found {len(items)} menu items. Target languages: {', '.join(target_langs)}")
    for item in items:
        _sync_one_item(item, target_langs, log, default_block_lang)
    return log
