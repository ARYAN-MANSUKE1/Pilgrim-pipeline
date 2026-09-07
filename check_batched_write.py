"""Self-check: batched write must cover every language and fall back cleanly.

WordPress charges its overhead per request, so all languages go in one POST.
That request is all-or-nothing, hence the fallback. Run: python check_batched_write.py
"""
from app.tasks import wp_client as wp

sent = {}
def fake_post(url, json=None, auth=None, timeout=None):
    sent.update(json["acf"])
    class R:
        status_code = 200
        def raise_for_status(self): pass
    return R()

wp.httpx.post = fake_post
items = {"ta": ("TitleTa", "BodyTa"), "bn": ("TitleBn", "BodyBn"), "pa": ("", "BodyPa")}
wp.write_all_translations(123, items)

# every language's content field must be present, in ONE request
for lang, (_, body) in items.items():
    assert sent[wp.CONTENT_FIELD_KEYS[lang]] == body, lang
assert sent[wp.TITLE_FIELD_KEYS["ta"]] == "TitleTa"
# an empty title must not blank the existing one
assert wp.TITLE_FIELD_KEYS["pa"] not in sent, "empty title would wipe the stored title"
# nothing to write -> no request at all
sent.clear()
wp.write_all_translations(123, {})
assert not sent
print(f"batched-write self-check OK ({len(items)} languages in 1 request)")
