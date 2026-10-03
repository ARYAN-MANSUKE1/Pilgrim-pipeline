"""
Is a translated field actually in the language it claims to be?

The pipeline's failure modes seen on the live audit: the batching marker
(zZqSEGqZz) leaking into published text, another language's text sitting in a
field (Marathi in the Malayalam box), and titles in the wrong script. These
checks are deliberately simple heuristics: Unicode script share, marker
words for the one pair (Marathi/Hindi) that shares a script.
"""

from __future__ import annotations

import html as _html
import re
from collections import Counter

MIN_CHARS = 200  # same threshold as the rest of the pipeline

_RANGE = {"mr": (0x0900, 0x097F), "hi": (0x0900, 0x097F), "gj": (0x0A80, 0x0AFF), "ta": (0x0B80, 0x0BFF),
          "te": (0x0C00, 0x0C7F), "kn": (0x0C80, 0x0CFF), "ml": (0x0D00, 0x0D7F), "bn": (0x0980, 0x09FF),
          "pa": (0x0A00, 0x0A7F)}
_MR = {"आहे", "आणि", "मध्ये", "येथे", "आहेत", "होते", "होती", "म्हणून"}
_HI = {"है", "और", "में", "था", "थी", "हैं", "यह", "इस"}
TOKEN_RE = re.compile(r"\s*zZ\w{2,12}Zz\s*")  # also catches the model's mangled variants


_TOKEN_STRIP_RE = re.compile(r"[ \t]*zZ\w{2,12}Zz[ \t]*")

# The model can get stuck repeating a syllable: one live Kannada article carried
# "ಳಿ" 2,352 times in a row -- right script, so no other check noticed. A short
# unit repeated 16+ times back to back never happens in real prose (longest real
# word across 23,000 live fields: 51 chars). Punctuation/digit runs are allowed:
# "?????" and "-----" occur in genuine source text.
_LOOP_RE = re.compile(r"(\S{1,6}?)\1{15,}")
_LOOP_OK = set(".-_=*~·•…।|/\\?!,:;0123456789")


def has_runaway_loop(text: str) -> bool:
    for m in _LOOP_RE.finditer(text):
        if not set(m.group(1)) <= _LOOP_OK:
            return True
    return False


def strip_token(html: str) -> str:
    """Remove the leaked marker. Only spaces/tabs around it are consumed, never
    newlines: blank lines are the paragraph breaks WordPress renders as <p>."""
    return _TOKEN_STRIP_RE.sub(" ", html or "")


def visible(s: str) -> str:
    s = re.sub(r"(?is)<(script|style).*?</\1>", " ", s or "")
    s = _html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"https?://\S+|\S+@\S+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def letter_counts(text: str) -> dict[str, int]:
    """Count of each alphabetic character. Counter() runs in C over the whole text,
    so the per-script maths below touches ~200 distinct characters, not 10,000."""
    return {c: n for c, n in Counter(text).items() if c.isalpha()}


def script_frac(text: str, lang: str) -> float:
    counts = letter_counts(text)
    total = sum(counts.values())
    if not total:
        return 0.0
    if lang == "en":
        return sum(n for c, n in counts.items() if c.isascii()) / total
    lo, hi = _RANGE[lang]
    return sum(n for c, n in counts.items() if lo <= ord(c) <= hi) / total


def _latin_ratio(text: str) -> float:
    words = [w for w in re.findall(r"[A-Za-z]{3,}", text) if not w.isupper()]
    return sum(map(len, words)) / max(1, sum(letter_counts(text).values()))


def _mr_hi(text: str) -> tuple[int, int]:
    toks = text.split()
    return sum(w in _MR for w in toks), sum(w in _HI for w in toks)


def content_problem(text: str, lang: str) -> str | None:
    """Reason this field is bad, or None. Fields under MIN_CHARS are 'empty', not 'bad'."""
    v = visible(text)
    if len(v) < MIN_CHARS:
        return None
    if TOKEN_RE.search(text):
        return "token leak"
    sf = script_frac(v, lang)
    if sf < (0.85 if lang == "en" else 0.6):
        return f"wrong script ({sf:.0%})"
    if lang != "en" and _latin_ratio(v) > 0.25:
        return "mostly Latin"
    if has_runaway_loop(v):
        return "runaway repetition"
    mr_c, hi_c = _mr_hi(v)
    if lang == "mr" and hi_c >= 5 and hi_c > 2 * mr_c:
        return "Hindi text in Marathi field"
    if lang == "hi" and mr_c >= 5 and mr_c > 2 * hi_c:
        return "Marathi text in Hindi field"
    return None


def mr_hi_duplicate(mr_text: str, hi_text: str) -> str | None:
    """Both share Devanagari, so an identical pair passes the script check. Say
    which one is the wrong-language copy ('mr' or 'hi'), or None if not a dup."""
    a, b = visible(mr_text), visible(hi_text)
    if len(a) < MIN_CHARS or re.sub(r"\W+", "", a) != re.sub(r"\W+", "", b):
        return None
    mr_c, hi_c = _mr_hi(a)
    return "mr" if hi_c > mr_c else "hi"  # ponytail: tie -> blame hi; ceiling = marker-word heuristic


def title_problem(title: str, lang: str, has_content: bool) -> str | None:
    t = (title or "").strip()
    if lang == "en":  # english_title is often unset; the WP post title serves
        return None
    if not t:
        return "title empty" if has_content else None
    if TOKEN_RE.search(t):
        return "token leak"
    if script_frac(t, lang) < 0.5:
        return "title in wrong script"
    return None


if __name__ == "__main__":
    assert content_problem("x" * 10, "ta") is None  # short = empty, not bad
    assert content_problem("Hello world " * 30, "ml") and "script" in content_problem("Hello world " * 30, "ml")
    assert content_problem("मंदिर आहे आणि येथे " * 20, "mr") is None
    assert content_problem("मंदिर है और यह " * 20, "mr") == "Hindi text in Marathi field"
    assert content_problem("இது கோவில் " * 30 + " zZqSEGqZz", "ta") == "token leak"
    assert title_problem("कसबा गणपती", "kn", True) == "title in wrong script"
    assert title_problem("", "en", True) is None
    assert strip_token("एक zZqSEGqZz दो\n\nतीन") == "एक दो\n\nतीन"  # paragraph break survives
    assert content_problem("ಈ ದೇವಾಲಯ ಬಹಳ ಪ್ರಾಚೀನ " * 12 + "ಎಂಬ" + "ಳಿ" * 40, "kn") == "runaway repetition"
    assert content_problem("ಈ ದೇವಾಲಯ ಬಹಳ ಪ್ರಾಚೀನ " * 20 + "??????????????????", "kn") is None  # source-text "????" is fine
    print("field_checks ok")
