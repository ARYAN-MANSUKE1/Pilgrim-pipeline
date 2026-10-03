"""
Translation that is checked before it is trusted.

Why this exists: the pipeline used to save whatever Gemini returned. On long
batches Gemini sometimes hands the Marathi input straight back -- batching
markers included, so the "did the markers survive" check passed -- and the tool
published it as a translation. About 1 temple in 4 ended up with a Marathi
article in a Malayalam/Tamil/Bengali box (and Marathi titles the same way).
Because the "don't overwrite existing content" guard only counted characters,
a re-run could never repair it.

So: every result is validated with the same checks the audit uses, a failed
attempt is retried in pieces small enough that no batching marker is used, and
if that also fails we raise instead of saving -- a visibly failed job that a
re-run will retry, never a silently wrong page.
"""

from __future__ import annotations

from typing import Callable

from app.tasks.field_checks import (MIN_CHARS, TOKEN_RE, content_problem, script_frac, strip_token,
                                    title_problem, visible)
from app.tasks.structured_translate import DEFAULT_MAX_CHARS, strip_cosmetic_spans, translate_html

TranslateFn = Callable[[str, str, str], str]

# Real Hindi translations share <=24% of their words with the Marathi article
# (measured on 2,116 temples); Marathi copies share ~90%. 0.7 cleanly separates them.
ECHO_OVERLAP = 0.7
# Length of a real translation vs its source, measured on 19,500 live articles:
# never below 0.52, 99% above 0.69, never above 1.23 (bar one runaway at 5.4x).
# Outside these bounds text was dropped, cut off, or the model looped.
MIN_LENGTH_RATIO = 0.5
MAX_LENGTH_RATIO = 2.5


class BadTranslation(RuntimeError):
    """A translation failed validation on every attempt. Nothing should be saved."""


def word_overlap(a_html: str, b_html: str) -> float:
    a, b = set(visible(a_html).split()), set(visible(b_html).split())
    return len(a & b) / max(1, len(a | b))


def article_problem(out_html: str, tgt: str, src_html: str, src: str) -> str | None:
    """Why `out_html` is not an acceptable translation of `src_html` into `tgt`, or None."""
    if TOKEN_RE.search(out_html):
        return "leaked batching marker"
    reason = content_problem(out_html, tgt)
    if reason:
        return reason
    src_len, out_len = len(visible(src_html)), len(visible(out_html))
    if out_len < MIN_LENGTH_RATIO * src_len:
        return f"far shorter than the source ({out_len} vs {src_len} characters)"
    if out_len > MAX_LENGTH_RATIO * src_len:
        return f"far longer than the source ({out_len} vs {src_len} characters)"
    if src != tgt and word_overlap(src_html, out_html) >= ECHO_OVERLAP:
        return "the source text handed back untranslated"
    return None


def translate_article(src_html: str, src: str, tgt: str, fn: TranslateFn) -> str:
    """Translate an article and return it only if it passes every check."""
    # A marker already sitting in the source would be copied into every language.
    # Cosmetic <span>s are stripped too: WordPress/Elementor wraps EVERY WORD in one, which shreds the
    # article into hundreds of fragments -- the batching marker then cannot survive, everything falls
    # back to one API call per word, and the result is translated word by word with no context.
    # (The dashboard pipeline already strips them; the repair path did not, which is why it was slow.)
    clean = strip_cosmetic_spans(strip_token(src_html))
    last = "no attempt made"
    # First the normal batched call; then one sentence per request, which uses no
    # batching marker at all (the thing Gemini echoes back). The failure is
    # repeatable for identical input, so retrying the same call would not help.
    for max_chars in (DEFAULT_MAX_CHARS, 1):
        out = translate_html(clean, src, tgt, fn, max_chars=max_chars)
        last = article_problem(out, tgt, clean, src)
        if last is None:
            return out
    raise BadTranslation(f"{tgt}: {last}")


def translate_title(candidates: list[tuple[str, str]], tgt: str, fn: TranslateFn) -> str | None:
    """Translate a title from the first candidate that yields a valid result.

    `candidates` is [(language, text), ...] best first -- pass the English title
    ahead of the Marathi one: told to keep names recognisable, Gemini returns a
    Devanagari title unchanged, but transliterates a Latin one into the target
    script. None if nothing valid came back (callers leave the title as it was).
    """
    for lang, text in candidates:
        if lang == tgt or not text.strip():
            continue
        for _ in range(2):
            out = fn(text, lang, tgt).strip()
            if (out and not TOKEN_RE.search(out) and out != text.strip()
                    and script_frac(out, tgt) >= (0.85 if tgt == "en" else 0.5)):
                return out
    return None


def content_needs_work(html: str, lang: str) -> bool:
    """True if a language's article is empty, a stub, or in the wrong language.

    This replaces "has >= 200 characters" as the test for "already translated":
    a Marathi copy in the Malayalam box has plenty of characters and is not.
    """
    return len(visible(html)) < MIN_CHARS or content_problem(html, lang) is not None


def title_needs_work(title: str, lang: str) -> bool:
    if lang == "en":
        # title_problem() ignores English because an unset english_title is harmless
        # to the audit (the WordPress page title serves). The pipeline still fills it.
        return not title.strip()
    return title_problem(title, lang, has_content=True) is not None
