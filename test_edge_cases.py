"""
Run: python test_edge_cases.py      (no API key, no network, nothing written anywhere)

Every way the translator has been seen to fail -- or plausibly could -- fed
through the REAL pipeline code (dashboard.pipeline._process) with a fake Gemini
and a fake WordPress. Each case must either save a correct translation or save
nothing and fail visibly. Never a wrong page.

Shaped like the 152 live-only temples: an English-only article with images,
translated into the other 9 languages.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")

import httpx

import dashboard.pipeline as pipe
from app.tasks import wp_client as wp
from app.tasks.field_checks import content_problem
from app.tasks.safe_translate import BadTranslation, article_problem, translate_article
from app.tasks.structured_translate import _SENTINEL_CORE

CF, TF = wp.CONTENT_FIELD_KEYS, wp.TITLE_FIELD_KEYS
TARGETS = ["mr", "hi", "gj", "ta", "te", "ml", "kn", "bn", "pa"]
# one character block per target script (Marathi/Hindi share Devanagari, told apart by marker words)
BLOCK = {"gj": 0x0A80, "ta": 0x0B80, "te": 0x0C00, "ml": 0x0D00, "kn": 0x0C80, "bn": 0x0980, "pa": 0x0A00}
MR_WORDS = "मंदिर आहे आणि येथे भाविक येतात आणि दर्शन घेतात "
HI_WORDS = "मंदिर है और यहाँ भक्त आते हैं और दर्शन करते हैं "

PARA = "This ancient temple of Lord Shiva stands on the river bank and thousands of pilgrims visit it every year. "
ENGLISH = ('<h3>Shiva Temple</h3>\n\n<img class="alignright" src="https://pilgrimdata.in/wp-content/uploads/a.jpg" alt="" width="300" />'
           + "\n\n".join(f"<p>{PARA * 3} Part {i}.</p>" for i in range(20))
           + '\n\n<img src="https://pilgrimdata.in/wp-content/uploads/b.jpg" alt="" />')


def good(text, src, tgt):
    """A script-correct 'translation' of about the length real ones have."""
    if tgt in BLOCK:
        base = BLOCK[tgt] + 0x15
        return " ".join("".join(chr(base + (ord(c) % 20)) for c in w) for w in text.split())
    unit = MR_WORDS if tgt == "mr" else HI_WORDS
    return (unit * (len(text) // len(unit) + 1))[: max(8, int(len(text) * 0.85))]


written = []
wp.refresh_language_fields = lambda: None
wp.write_all_translations = lambda pid, items: written.append(dict(items))
wp.write_title_and_content = lambda pid, lang, title, html: written.append({lang: (title, html)})


def run(gemini, extra_acf=None, languages=None, source=None):
    acf = {CF["en"]: ENGLISH}
    acf.update(extra_acf or {})
    pipe._fetch = lambda pid: {"id": pid, "slug": "t", "acf": acf,
                               "title": {"raw": "Shiva Temple, Ozar, Dist. Pune", "rendered": "Shiva Temple, Ozar, Dist. Pune"}}
    pipe.gtranslate = gemini
    del written[:]
    msgs = []
    err = None
    try:
        pipe.process_temple(1, operation="translate", languages=languages, source=source, log=msgs.append)
    except Exception as e:  # noqa: BLE001
        err = e
    saved = {}
    for w in written:
        saved.update(w)
    return saved, err, msgs


def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        raise SystemExit(1)


# 1. The happy path for the 152: English-only temple -> all 9 languages saved, titles in each script.
saved, err, _ = run(good)
check("English-only temple: all 9 languages saved", err is None and sorted(saved) == sorted(TARGETS))
check("every saved article passes every check",
      all(article_problem(h, l, ENGLISH, "en") is None for l, (t, h) in saved.items()))
check("both images kept in every language", all(h.count("<img") == 2 for t, h in saved.values()))
check("titles saved in each language (from the English title)", all(t for t, h in saved.values()))

# 2. Gemini writes HINDI when asked for Marathi (same script, only marker words differ) -> nothing saved for mr.
def hindi_for_marathi(text, src, tgt):
    return good(text, src, "hi") if tgt == "mr" else good(text, src, tgt)
saved, err, _ = run(hindi_for_marathi)
check("Hindi returned for Marathi is rejected, the other 8 still saved", "mr" not in saved and len(saved) == 8 and err)

# 3. Gemini cuts the article short (40% of the text) -> rejected.
def truncated(text, src, tgt):
    return good(text, src, tgt)[: int(len(text) * 0.35)] if len(text) > 300 else good(text, src, tgt)
check("an article cut to ~35% is rejected",
      article_problem(translate_html_safe := __import__("app.tasks.structured_translate", fromlist=["x"]).translate_html(
          ENGLISH, "en", "ta", truncated, max_chars=6000), "ta", ENGLISH, "en") is not None)

# 4. Gemini loops ("ಳಿಳಿಳಿ...") -> rejected, falls back, still bad -> nothing saved for kn.
def loops_in_kannada(text, src, tgt):
    return good(text, src, tgt) + (" ಎಂಬ" + "ಳಿ" * 60 if tgt == "kn" else "")
saved, err, _ = run(loops_in_kannada)
check("a runaway loop in Kannada is rejected, others saved", "kn" not in saved and len(saved) == 8 and err)

# 5. Gemini hands the English back untouched when batched (the original 1-in-4 bug) -> retried per sentence, saved.
def echo_when_batched(text, src, tgt):
    return text if _SENTINEL_CORE in text else good(text, src, tgt)
saved, err, _ = run(echo_when_batched)
check("batched echo recovers via the per-sentence retry: all 9 saved", err is None and len(saved) == 9)

# 6. Gemini leaks the batching marker into its output -> rejected on that attempt.
check("a leaked batching marker is caught",
      article_problem(good(ENGLISH, "en", "te") + " zZqSEGqZz", "te", ENGLISH, "en") == "leaked batching marker")

# 7. Provider out of credit (402) for every call -> job fails, NOTHING saved.
def out_of_credit(text, src, tgt):
    raise httpx.HTTPStatusError("402 Payment Required", request=httpx.Request("POST", "https://x"),
                                response=httpx.Response(402))
saved, err, _ = run(out_of_credit)
check("402 out-of-credit: job fails and saves nothing", saved == {} and err is not None)

# 8. One language's provider call keeps failing -> the other 8 are saved, the job still reports failure.
def ta_down(text, src, tgt):
    if tgt == "ta":
        raise httpx.ConnectError("boom")
    return good(text, src, tgt)
saved, err, _ = run(ta_down)
check("one language down: other 8 saved, job reported as failed", len(saved) == 8 and "ta" not in saved and err)

# 9. ...and re-running afterwards only redoes the missing language (already-correct ones are left alone).
done = {CF[l]: saved[l][1] for l in saved}
done.update({TF[l]: saved[l][0] for l in saved})
# With no source given, the pipeline's staging rule (Marathi first) would now pick the freshly machine-translated
# Marathi as the source -- a translation of a translation. translate_live.py pins the source to English for this
# reason; this checks that pinned behaviour.
saved2, err2, _ = run(good, extra_acf=done, source="en")
check("re-run (source pinned to English) fills only the gap: Tamil", sorted(saved2) == ["ta"] and err2 is None)

# 10. Source itself is in the wrong language -> refuse the whole temple instead of spreading it to 9 languages.
saved, err, _ = run(good, extra_acf={CF["en"]: good(ENGLISH, "en", "te")})
check("a source in the wrong language is refused, nothing saved", saved == {} and err is not None)

# 11. Source too short to translate (a stub) -> refused.
saved, err, _ = run(good, extra_acf={CF["en"]: "<p>Coming soon.</p>"})
check("a stub source is refused", saved == {} and err is not None)

# 12. Source has a <span> around every word (WordPress editor output) -> still a handful of calls, no spans kept.
calls = []
def counting(text, src, tgt):
    calls.append(1)
    return good(text, src, tgt)
spanny = "<p>" + " ".join(f'<span style="font-weight: 400;">{w}</span>' for w in (PARA * 30).split()) + "</p>"
out = translate_article(spanny, "en", "ml", counting)
check(f"per-word <span> source: {len(calls)} call(s), no spans left", len(calls) <= 6 and "<span" not in out)

# 13. Gemini returns nothing at all -> never an empty article saved.
saved, err, _ = run(lambda t, s, g: "")
check("empty replies: nothing saved", all(h.strip() for t, h in saved.values()) and len(saved) < 9)

print("\nall edge cases passed")
