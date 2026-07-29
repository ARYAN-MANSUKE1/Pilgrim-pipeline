"""
Translate the site's fixed UI "chrome" (nav labels, footer menu, social labels,
copyright) into a language ONCE, so the frontend serves cached strings instead of
re-translating on every page load.

This is a tiny, FIXED set of strings for the whole site (it does not grow with the
number of temples). When a new language is added in the tool, call
translate_ui_strings(lang) once, store the result in a WordPress option
(pilgrim_ui_i18n), and the theme reads it forever after. English is the guaranteed
fallback, so a missing/failed string is never blank.

Uses the same Gemini engine as temple content (app.tasks.gemini_translate).
"""

from __future__ import annotations

from app.tasks.gemini_translate import translate as gtranslate

# Canonical UI strings in English (the source of truth). The KEYS are stable ids
# the theme tags onto each element (e.g. data-i18n="nav_home"). Keep in sync with
# the tags in functions.php / Elementor. Add a key here only when the site gains a
# new piece of translatable chrome — NOT when a language is added.
UI_STRINGS_EN: dict[str, str] = {
    "nav_home":     "Home",
    "nav_about":    "About Us",
    "nav_temples":  "Temples",
    "nav_state":    "State",
    "nav_sponsors": "Sponsors",
    "nav_contact":  "Contact Us",
    "nav_privacy":  "Privacy Policy",
    "nav_terms":    "Terms & Conditions",
    "s_instagram":  "Instagram",
    "s_facebook":   "Facebook",
    "s_youtube":    "YouTube",
    "copyright":    "All Rights Reserved.",
}


def translate_ui_strings(target_lang: str, source_lang: str = "en") -> dict[str, str]:
    """
    Translate the fixed UI chrome into target_lang. Returns {key: text}.

    - English (== source_lang) is returned as-is, no API calls.
    - One short Gemini call per string; this runs ONCE per language, not per request.
    - Any string that fails to translate falls back to its English text, so the
      returned dict always has every key (the frontend can never render blank).
    """
    if target_lang == source_lang:
        return dict(UI_STRINGS_EN)

    out: dict[str, str] = {}
    for key, text in UI_STRINGS_EN.items():
        try:
            translated = (gtranslate(text, source_lang, target_lang) or "").strip()
            out[key] = translated or text          # empty result -> English
        except Exception:
            out[key] = text                        # engine error -> English; never blank
    return out


if __name__ == "__main__":
    # Self-check (no network): english passthrough + guaranteed English fallback.
    assert translate_ui_strings("en") == UI_STRINGS_EN, "english must pass through unchanged"

    _boom = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("engine down"))
    globals()["gtranslate"] = _boom                # force every translation to fail (this namespace)
    fell_back = translate_ui_strings("ur")         # Urdu, but engine is "down"
    assert fell_back == UI_STRINGS_EN, "failed strings must fall back to English"
    assert set(fell_back) == set(UI_STRINGS_EN), "every key must always be present"
    print(f"ui_strings self-check OK — {len(UI_STRINGS_EN)} chrome strings, English-safe")
