"""
Text normalization for TTS input.

Temple addresses use abbreviations (Marathi `ता.` = तालुका, `जि.` = जिल्हा;
English `Tal.`/`Dist.`) that Sarvam reads out literally ("ta", "ji") instead of
the full word. Gemini already expands these when it *translates*, so target
languages are fine — but the SOURCE-language audio (usually Marathi) still has
the raw abbreviations. This expands them for speech only; it never touches the
text stored/displayed on the site.

Multi-token forms (जि. प. = जिल्हा परिषद) are listed before single ones so the
longer match wins. Patterns consume trailing spaces and re-add a single space,
so both "ता. जत" and "ता.जत" normalize cleanly.
"""

from __future__ import annotations

import re

_ABBREVIATIONS: dict[str, list[tuple[str, str]]] = {
    "mr": [
        (r"जि\.\s*प\.\s*", "जिल्हा परिषद "),
        (r"ग्रा\.\s*पं\.\s*", "ग्रामपंचायत "),
        (r"मु\.\s*पो\.\s*", "मुक्काम पोस्ट "),
        (r"ता\.\s*", "तालुका "),
        (r"जि\.\s*", "जिल्हा "),
        (r"मु\.\s*", "मुक्काम "),
        (r"पो\.\s*", "पोस्ट "),
    ],
    "hi": [
        (r"जि\.\s*प\.\s*", "जिला परिषद "),
        (r"तह\.\s*", "तहसील "),
        (r"ता\.\s*", "तालुका "),   # carried over untranslated from the Marathi source
        (r"जि\.\s*", "जिला "),
    ],
    "en": [
        (r"\bTal\.", "Taluka"),
        (r"\bTq\.", "Taluka"),
        (r"\bTa\.", "Taluka"),
        (r"\bDist\.", "District"),
        (r"\bDt\.", "District"),
        (r"\bPO\.", "Post Office"),
    ],
    # The Marathi "ता./जि." survives translation into every Indic language as
    # the same bare abbreviation, and each language's voice reads it as the
    # meaningless syllables "ta"/"ji". Words verified against Sarvam's
    # translate API, and cross-checked against Tamil/Malayalam, whose content
    # already came through fully expanded (தாலுகா/மாவட்டம், താലൂക്ക്/ജില്ല).
    "gj": [(r"તા\.\s*", "તાલુકા "), (r"જિ\.\s*", "જિલ્લો ")],
    "te": [(r"తా\.\s*", "తాలూకా "), (r"జి\.\s*", "జిల్లా ")],
    "kn": [(r"ತಾ\.\s*", "ತಾಲ್ಲೂಕು "), (r"ಜಿ\.\s*", "ಜಿಲ್ಲೆ ")],
    "bn": [(r"তা\.\s*", "তালুকা "), (r"জি\.\s*", "জেলা ")],
    "pa": [(r"ਤਾ\.\s*", "ਤਾਲੁਕਾ "), (r"ਜ਼ਿ\.\s*", "ਜ਼ਿਲ੍ਹਾ ")],
    # Malayalam already has the full words, but with a stray period after each
    # ("താലൂക്ക്. ജില്ല.") that reads as a sentence break mid-address.
    "ml": [(r"താലൂക്ക്\.\s*", "താലൂക്ക് "), (r"ജില്ല\.\s*", "ജില്ല ")],
}

# Pre-compile for speed.
#
# The leading lookbehind is load-bearing: it requires the abbreviation to START
# a token, so an ordinary word that merely ENDS in those letters before a full
# stop is left alone. Without it "ता\." also matches the tail of होता. / ओळखाता.
# and rewrites the end of a normal sentence into "...होतालुका" -- confirmed
# happening 4 times in one temple's real text.
#
# It has to be a WHITELIST of separators, not a "not a word character" test:
# Devanagari and Gujarati matras (े ा ो) are combining marks, which Python's
# \w does NOT treat as word characters, so a "not \w" lookbehind happily
# matched right after the ो of होता and corrupted it anyway.
_TOKEN_START = r"(?<![^\s,;:।॥()\[\]{}\"'‘’“”\-–—/])"

_COMPILED = {
    lang: [(re.compile(_TOKEN_START + p), r) for p, r in rules]
    for lang, rules in _ABBREVIATIONS.items()
}


def expand_abbreviations(text: str, lang: str) -> str:
    """Expand address/temple abbreviations for the given language, for TTS only."""
    if not text:
        return text
    for pat, rep in _COMPILED.get(lang, []):
        text = pat.sub(rep, text)
    return text


# ---------------------------------------------------------------------------
# Numbers -> spoken words (English)
# ---------------------------------------------------------------------------
#
# Sarvam's TTS reads a bare "1893" digit-by-digit ("one eight nine three"), so
# years and measurements have to be spelled out before it ever sees them.
# For the Indic languages the transliterate API does this (source==target with
# spoken_form=True); for ENGLISH that call is a no-op, so it's done here.
#
# `\d` is Unicode-aware, so this matches Devanagari (१८९३) and other Indic
# digits as well as ASCII -- used by the caller to FIND numbers in any script.
# Digit groups may carry grouping commas, in Western (16,000) or Indian
# (1,68,864) style -- matching only "\d+" split those into "sixteen" + "000".
_DIGITS = r"\d+(?:,\d+)+|\d+"

# English also takes an ordinal ending: 1st / 2nd / 3rd / 10th / 16th-century.
NUMBER_RE = re.compile(rf"(?:{_DIGITS})(?:[.:]\d+)+|(?:{_DIGITS})(?:st|nd|rd|th)?")

# Same, but also swallowing a case-ending glued straight onto the digits:
# Kannada १८९३ರಲ್ಲಿ ("in 1893"), Malayalam 1893-ൽ, Telugu 1893లో.
#
# The ending has to go to Sarvam WITH the number, because the spelled-out form
# inflects: 1893ರಲ್ಲಿ is ...ತೊಂಬತ್ತಮೂರರಲ್ಲಿ, not ...ತೊಂಬತ್ತಮೂರು + ರಲ್ಲಿ
# (which is what expanding the digits alone produced -- a doubled ರು), and
# 1893-ൽ is ...മൂന്നിൽ, not ...മൂന്ന് + "-ൽ" with the hyphen read aloud.
#
# Indic-only: English never glues a case ending on, and letting it capture one
# would turn "1890s" into something int() cannot parse.
#
# The trailing class is a NEGATED set rather than \w because Indic vowel signs
# and viramas are combining marks that \w does not match -- \w would clip
# "ರಲ್ಲಿ" mid-cluster.
NUMBER_WITH_SUFFIX_RE = re.compile(
    rf"(?:{_DIGITS})(?:[.:]\d+)*(?:-?[^\s\d.,;:।॥()\[\]{{}}\"'‘’“”/–—]+)?"
)

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve "
         "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")


def _under_hundred(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, rest = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[rest]}" if rest else "")


def _under_thousand(n: int) -> str:
    if n < 100:
        return _under_hundred(n)
    hundreds, rest = divmod(n, 100)
    return f"{_ONES[hundreds]} hundred" + (f" {_under_hundred(rest)}" if rest else "")


def english_cardinal(n: int) -> str:
    """1893 -> 'one thousand eight hundred ninety-three'."""
    if n == 0:
        return "zero"
    parts = []
    for div, name in ((1_000_000, "million"), (1000, "thousand")):
        if n >= div:
            q, n = divmod(n, div)
            parts.append(f"{_under_thousand(q)} {name}")
    if n:
        parts.append(_under_thousand(n))
    return " ".join(parts)


def english_year(n: int) -> str:
    """1893 -> 'eighteen ninety-three', 2024 -> 'twenty twenty-four',
    1900 -> 'nineteen hundred', 1905 -> 'nineteen oh five', 2000 -> 'two thousand'."""
    if n % 1000 == 0:            # 2000 reads as "two thousand", not "twenty hundred"
        return english_cardinal(n)
    high, low = divmod(n, 100)
    if low == 0:
        return f"{_under_hundred(high)} hundred"
    if low < 10:
        return f"{_under_hundred(high)} oh {_ONES[low]}"
    return f"{_under_hundred(high)} {_under_hundred(low)}"


# Ordinals whose word is irregular; everything else takes -th, and a tens word
# ending in -y becomes -ieth (twenty -> twentieth).
_ORDINAL_IRREGULAR = {
    "one": "first", "two": "second", "three": "third", "five": "fifth",
    "eight": "eighth", "nine": "ninth", "twelve": "twelfth",
}


def english_ordinal(n: int) -> str:
    """1 -> first, 2 -> second, 10 -> tenth, 21 -> twenty-first, 20 -> twentieth."""
    words = english_cardinal(n)
    head, sep, last = words.rpartition(" ")
    stem, hyphen, core = last.rpartition("-")     # "twenty-one" -> ordinalise "one"
    if core in _ORDINAL_IRREGULAR:
        core = _ORDINAL_IRREGULAR[core]
    elif core.endswith("y"):
        core = core[:-1] + "ieth"
    else:
        core += "th"
    return head + sep + stem + hyphen + core


def _is_clock(whole: str, frac: str) -> bool:
    """
    True for H.MM / H:MM written as a time rather than a decimal.

    Decided by the fraction's WIDTH, which the corpus separates cleanly:
    every 2-digit fraction is a time (५.३० वाजल्यापासून, ७.१५ वाजता -- 336 of
    them) and every 1-digit fraction is a measurement (1.5 km, ६.६ कोटी -- 50).
    """
    return (len(frac) == 2 and whole.isdigit()
            and int(whole) <= 24 and int(frac) <= 59)


def english_number_phrase(token: str) -> str:
    """
    One matched number token -> spoken English.
      "1893"    -> eighteen ninety-three   (year range reads year-style)
      "1,68,864"-> one lakh sixty-eight thousand eight hundred sixty-four value
      "3rd"     -> third
      "7.5"     -> seven point five
      "5:30"    -> five thirty
      "5.30"    -> five thirty            (2-digit fraction is a clock time)
    """
    ordinal = False
    for suffix in ("st", "nd", "rd", "th"):
        if token.endswith(suffix) and token[:-2]:
            token, ordinal = token[:-2], True
            break
    token = token.replace(",", "")                    # grouping commas: 16,000

    for sep in (":", "."):
        if sep in token:
            whole, _, frac = token.partition(sep)
            if _is_clock(whole, frac):
                mins = "o'clock" if int(frac) == 0 else _under_hundred(int(frac))
                return f"{_under_hundred(int(whole))} {mins}".strip()
            if sep == ".":                            # a decimal: read digits after the point
                digits = " ".join(_ONES[int(d)] for d in frac if d.isdigit())
                return f"{english_cardinal(int(whole))} point {digits}"
            mins = "o'clock" if int(frac) == 0 else _under_hundred(int(frac))
            return f"{_under_hundred(int(whole))} {mins}".strip()

    n = int(token)
    if ordinal:
        return english_ordinal(n)
    if 1100 <= n <= 2099:                             # plausible year
        return english_year(n)
    return english_cardinal(n)
