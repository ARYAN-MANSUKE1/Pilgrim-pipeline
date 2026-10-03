"""
One-off: the live nav menu's Kannada "Terms & Conditions" label contains a
Telugu vowel sign (U+0C41) where the Kannada one (U+0CC1) belongs. Fixes that
single character in every live menu item, touching nothing else.

    python fix_kannada_nav.py          # show what would change
    python fix_kannada_nav.py --go     # apply it
"""
import re
import sys

import httpx

from app.config import settings

TELUGU_U, KANNADA_U = "ు", "ು"
API = settings.live_wp_url.rstrip("/") + "/wp-json/wp/v2/menu-items"
AUTH = (settings.live_wp_user, settings.live_wp_app_password)
GO = "--go" in sys.argv

items = httpx.get(API, params={"per_page": 100, "context": "edit"}, auth=AUTH, timeout=60).json()
changed = 0
for it in items:
    raw = it["title"]["raw"]

    def fix(m):
        return m.group(1) + m.group(2).replace(TELUGU_U, KANNADA_U) + m.group(3)

    new = re.sub(r'(<div class="kn_lang dis_lang"[^>]*>)(.*?)(</div>)', fix, raw, flags=re.S)
    if new != raw:
        changed += 1
        print(f"menu item {it['id']}: fixing the Kannada label" + ("" if GO else "  (dry run)"))
        if GO:
            httpx.post(f"{API}/{it['id']}", json={"title": new}, auth=AUTH, timeout=60).raise_for_status()
print(f"{changed} item(s) {'fixed' if GO else 'would be fixed'}.")
