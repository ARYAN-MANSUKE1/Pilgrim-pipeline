"""
One-time (or re-run-anytime) seed: translate the site's fixed UI chrome into
every current language and push it into WordPress (pilgrim_ui_i18n option).

This is what makes the footer/header/nav labels show correctly in every
language again after the migration wiped the old per-language Elementor
blocks — and, going forward, survives any future reset because it lives in
wp_options instead of Elementor.

Run:  python seed_ui_i18n.py
      python seed_ui_i18n.py bn pa       # only these languages
"""

import sys

from app.tasks.push_ui_i18n import push_ui_strings
from app.tasks.ui_strings import UI_STRINGS_EN, translate_ui_strings

ALL_LANGS = ("mr", "en", "hi", "gj", "ta", "te", "ml", "kn", "bn", "pa")


def main():
    langs = sys.argv[1:] or ALL_LANGS
    print(f"Seeding chrome strings ({len(UI_STRINGS_EN)} keys) for: {', '.join(langs)}\n")
    for lang in langs:
        try:
            strings = translate_ui_strings(lang)
            result = push_ui_strings(lang, strings)
            print(f"[{lang}] saved {result.get('keys_saved')} keys")
        except Exception as e:
            print(f"[{lang}] FAILED: {e}")
    print("\nDone. Verify on the site by switching languages in the dropdown.")


if __name__ == "__main__":
    main()
