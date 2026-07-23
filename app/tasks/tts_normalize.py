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
}

# Pre-compile for speed.
_COMPILED = {
    lang: [(re.compile(p), r) for p, r in rules]
    for lang, rules in _ABBREVIATIONS.items()
}


def expand_abbreviations(text: str, lang: str) -> str:
    """Expand address/temple abbreviations for the given language, for TTS only."""
    if not text:
        return text
    for pat, rep in _COMPILED.get(lang, []):
        text = pat.sub(rep, text)
    return text
