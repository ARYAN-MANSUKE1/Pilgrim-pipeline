"""
Run: python test_safe_translate.py      (no API key, no network)

Reproduces the production failure with a fake "Gemini" that hands the source
straight back whenever the batching marker is in the request -- the behaviour
seen on 1 temple in 4 -- and checks the pipeline can no longer save that.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.tasks.safe_translate import (BadTranslation, article_problem, content_needs_work, title_needs_work,
                                      translate_article, translate_title, word_overlap)
from app.tasks.structured_translate import _SENTINEL_CORE, translate_html


def to_malayalam(text: str) -> str:
    """A fake but script-correct 'translation': shift Devanagari into the Malayalam block."""
    return "".join(chr(ord(c) + 0x400) if 0x900 <= ord(c) <= 0x97F else c for c in text)


PARA = "श्री शंकराचे प्राचीन मंदिर नदीच्या काठी आहे आणि दरवर्षी हजारो भाविक येथे येतात. "
MARATHI = "<h3>मंदिर</h3>\n\n" + "\n\n".join(f"<p>{PARA * 2} भाग {i}</p>" for i in range(25))


def echo_when_batched(text, src, tgt):
    """Production behaviour: given the marker-joined batch, return the input untouched."""
    return text if _SENTINEL_CORE in text else to_malayalam(text)


def always_echo(text, src, tgt):
    return text


# 1. The flaw, reproduced: the OLD call (6000-char batches, no validation) yields a Marathi
#    "Malayalam" article that the old sentinel-count check accepted, and the checker sees it.
old = translate_html(MARATHI, "mr", "ml", echo_when_batched, max_chars=6000)
assert _SENTINEL_CORE not in old, "the marker count survived, so the old code saw a valid translation"
assert article_problem(old, "ml", MARATHI, "mr"), "the new checks must flag it"
print("1 ok: old behaviour reproduced and flagged:", article_problem(old, "ml", MARATHI, "mr"))

# 2. The fix: the first (batched) try is rejected, the marker-free retry succeeds and is saved.
good = translate_article(MARATHI, "mr", "ml", echo_when_batched)
assert article_problem(good, "ml", MARATHI, "mr") is None
assert "<h3>" in good and good.count("<p>") == MARATHI.count("<p>"), "HTML structure must survive"
print("2 ok: batched echo rejected, retried without the marker, valid Malayalam saved")

# 3. If Gemini never translates, raise -- never return the source as if it were a translation.
try:
    translate_article(MARATHI, "mr", "ml", always_echo)
    raise SystemExit("FAIL: an always-echoing Gemini must not produce a result")
except BadTranslation as e:
    print("3 ok: refuses to save an untranslated article:", e)

# 4. Marathi <-> Hindi share a script, so only word overlap catches a copy.
assert word_overlap(MARATHI, MARATHI) == 1.0
assert article_problem(MARATHI, "hi", MARATHI, "mr") == "Marathi text in Hindi field"   # marker words give it away
NEUTRAL = "<p>" + "श्री गणेश मंदिर पुणे शहर पर्वती परिसर प्राचीन स्थान दर्शन पूजा उत्सव वेळ " * 8 + "</p>"
assert article_problem(NEUTRAL, "hi", NEUTRAL, "mr") == "the source text handed back untranslated"  # no marker words: overlap catches it
HINDI = "<p>" + "यह श्री गणेश का प्राचीन मंदिर है और यहाँ हर वर्ष हजारों श्रद्धालु दर्शन के लिए आते हैं। " * 8 + "</p>"
assert article_problem(HINDI, "hi", NEUTRAL, "mr") is None, "a real Hindi translation must not be flagged"
print("4 ok: a Marathi copy in the Hindi field is caught, a real Hindi translation is not")

# 5. The 'already translated' guard is about the language, not the character count.
assert content_needs_work(MARATHI, "ml") is True          # Marathi in the Malayalam box: redo it
assert content_needs_work(to_malayalam(MARATHI), "ml") is False
assert content_needs_work("", "ml") is True
assert content_needs_work(MARATHI + " zZqSEGqZz", "mr") is True   # leaked marker
print("5 ok: guard treats wrong-language text as needing work")

# 6. Titles: English first (Gemini transliterates it), Marathi only as a fallback, None if nothing valid.
def title_fn(text, src, tgt):
    return "ശ്രീ ക്ഷേത്രം" if src == "en" else text            # copies a Devanagari title back
assert translate_title([("en", "Shri Temple"), ("mr", "श्री मंदिर")], "ml", title_fn) == "ശ്രീ ക്ഷേത്രം"
assert translate_title([("mr", "श्री मंदिर")], "ml", title_fn) is None
assert title_needs_work("श्री मंदिर", "ml") is True and title_needs_work("ശ്രീ ക്ഷേത്രം", "ml") is False
assert title_needs_work("", "en") is True and title_needs_work("Shri Temple", "en") is False   # english_title is still filled
print("6 ok: titles come from English and are never a copy of the Marathi one")

print("\nall checks passed")

# 10. A source with a <span> around EVERY word (what WordPress/Elementor produces) must be translated
#     in a handful of calls, not one call per word.
SPANNY = "<p>" + " ".join(f'<span style="font-weight: 400;">{w}</span>' for w in (PARA * 12).split()) + "</p>"
n_calls = []
def counting(text, src, tgt):
    n_calls.append(1)
    return to_malayalam(text)
out = translate_article(SPANNY, "mr", "ml", counting)
assert len(n_calls) <= 6, f"per-word spans exploded into {len(n_calls)} calls"
assert "<span" not in out
print(f"10 ok: a per-word-<span> article took {len(n_calls)} call(s), not ~{len(SPANNY.split('<span')) - 1}")

# ---------------------------------------------------------------------------
# 7-9. The real pipeline flow (dashboard.pipeline._process) with a fake WordPress and a fake Gemini
# ---------------------------------------------------------------------------
from app.tasks import wp_client as wp
import dashboard.pipeline as pipe

written = []
wp.refresh_language_fields = lambda: None
wp.write_all_translations = lambda post_id, items: written.append(dict(items))
wp.write_title_and_content = lambda post_id, lang, title, html: written.append({lang: (title, html)})


def flawed_gemini(text, src, tgt):
    if _SENTINEL_CORE in text:
        return text                                            # batched: hands the source back
    if src == "en":
        return "ശ്രീ ശങ്കര ക്ഷേത്രം"                          # an English title is transliterated
    return to_malayalam(text) if len(text) > 60 else text      # a short Marathi title is copied back


def run_flow(acf_extra, gemini):
    acf = {wp.CONTENT_FIELD_KEYS["mr"]: MARATHI, wp.TITLE_FIELD_KEYS["mr"]: "श्री शंकर मंदिर"}
    acf.update(acf_extra)
    pipe._fetch = lambda pid: {"id": pid, "slug": "t", "acf": acf,
                               "title": {"raw": "Shri Shankar Temple", "rendered": "Shri Shankar Temple"}}
    pipe.gtranslate = gemini
    del written[:]
    msgs = []
    pipe.process_temple(1, operation="translate", languages=["ml"], log=msgs.append)
    return msgs


# 7. THE PRODUCTION CASE: Marathi article + Marathi title already sitting in the Malayalam fields.
bad = {wp.CONTENT_FIELD_KEYS["ml"]: MARATHI, wp.TITLE_FIELD_KEYS["ml"]: "श्री शंकर मंदिर"}
msgs = run_flow(bad, flawed_gemini)
title, html = written[0]["ml"]
assert article_problem(html, "ml", MARATHI, "mr") is None, "the saved article must be real Malayalam"
assert title == "ശ്രീ ശങ്കര ക്ഷേത്രം", "the title must come from the English one"
assert any("wrong language" in m for m in msgs), msgs
print("7 ok: a Marathi copy in the Malayalam box is now REPLACED with a real translation (old guard skipped it)")

# 8. Already correct -> nothing is bought or overwritten.
good_acf = {wp.CONTENT_FIELD_KEYS["ml"]: to_malayalam(MARATHI), wp.TITLE_FIELD_KEYS["ml"]: "ശ്രീ ശങ്കര ക്ഷേത്രം"}
msgs = run_flow(good_acf, flawed_gemini)
assert written == [], "a correct language must be left alone"
print("8 ok: a correct translation is left alone")

# 9. Gemini never translates -> the job FAILS and saves nothing (never a silently wrong page).
try:
    run_flow(bad, always_echo)
    raise SystemExit("FAIL: a job that could not translate must not report success")
except RuntimeError as e:
    assert written == [], "nothing may be saved"
    print("9 ok: untranslatable article -> job fails visibly, nothing saved:", str(e)[:70])

print("\nall checks passed (unit + full pipeline flow)")
