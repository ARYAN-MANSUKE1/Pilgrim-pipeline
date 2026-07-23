"""
Structure-preserving HTML translation for WordPress temple content.

Temple content is WP-editor HTML: block-level tags (<h1>/<h3>/<ul>/<li>),
inline <img> tags with alignment classes, and paragraphs separated by BLANK
lines (\\n\\n) that WordPress' wpautop() turns into <p>. A naive "translate the
whole blob" call collapses those blank lines and can rewrite the <img> tags,
which destroys the layout: wall-of-text, images floating into the gallery.

This module translates ONLY the human-readable text and never sends a single
HTML tag to the translation API, so every tag, image, and paragraph break comes
back byte-for-byte identical. Only the words change.

Design:
  1. Split the document into blocks on blank lines, KEEPING the separators.
  2. Within each block, split into text/tag tokens; tags are never touched.
  3. Bin-pack the translatable text tokens into <=max_chars requests (minimises
     API calls -> avoids rate limits) joined by a sentinel.
  4. Translate each batch; split on the sentinel. If the sentinel count doesn't
     survive, fall back to translating that batch's tokens one by one (correct,
     just a few more calls). So correctness never depends on the sentinel.
  5. Reassemble tokens and rejoin blocks with the original separators.

The translate function is injected: (text, source_lang, target_lang) -> text.
That keeps this module dependency-free (stdlib only) and unit-testable without
any API key, and lets it drop into either sample.py or the production pipeline.
"""

from __future__ import annotations

import re
from typing import Callable, Dict, List

# (text, source_lang, target_lang) -> translated text
TranslateFn = Callable[[str, str, str], str]

# Capturing group so re.split keeps the tags in the result.
_TAG_RE = re.compile(r"(<[^>]+>)")
_FULL_TAG_RE = re.compile(r"^<[^>]+>$")
# One or more blank lines between blocks (allowing stray spaces/tabs on the blank line).
_BLOCK_SEP_RE = re.compile(r"((?:\r?\n[ \t]*){2,})")
# Sentence-ish boundaries, incl. the Devanagari danda, for splitting over-long segments.
_SENTENCE_RE = re.compile(r"[^।.!?\n]*[।.!?\n]|[^।.!?\n]+")

# A distinctive nonsense token unlikely to be altered by a translator. We still
# verify it survived and fall back per-segment if not, so it need not be perfect.
_SENTINEL_CORE = "zZqSEGqZz"
_SENTINEL = f" {_SENTINEL_CORE} "
_SENTINEL_SPLIT_RE = re.compile(r"\s*" + _SENTINEL_CORE + r"\s*")

# Sarvam Translate caps a request at 2000 chars; leave headroom.
DEFAULT_MAX_CHARS = 1800


_SPAN_RE = re.compile(r"</?span\b[^>]*>", re.IGNORECASE)


def strip_cosmetic_spans(html: str) -> str:
    """Remove <span> wrappers (WordPress/Elementor adds one per word, e.g.
    style="font-weight: 400"), keeping the inner text. They're visually
    identical to plain text but bloat the HTML ~7x and fragment translation
    into one API call per word. Real structure (<h1>/<ul>/<img>) is untouched."""
    if not html:
        return html
    return _SPAN_RE.sub("", html)


def strip_tags(html: str) -> str:
    """Plain, readable text for TTS input: drop HTML tags/<img>, keep sentence flow.
    Paragraph breaks become single newlines so the audio has natural pauses."""
    if not html:
        return ""
    text = _TAG_RE.sub(" ", html)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*\n\s*", "\n", text)
    return text.strip()


def _is_translatable(text: str) -> bool:
    """True if the token has real words (letters/digits), not just whitespace/punctuation."""
    return bool(text) and bool(re.search(r"\w", text, re.UNICODE))


def _is_tag(token: str) -> bool:
    return bool(_FULL_TAG_RE.match(token))


def _preserve_edge_ws(original: str, translated: str) -> str:
    """Reattach the original leading/trailing whitespace (spacing around inline tags matters)."""
    lead = original[: len(original) - len(original.lstrip())]
    trail = original[len(original.rstrip()):]
    return f"{lead}{translated.strip()}{trail}"


# ---------------------------------------------------------------------------
# Translating a flat list of text segments, bin-packed to minimise API calls
# ---------------------------------------------------------------------------

def _translate_one(text: str, src: str, tgt: str, fn: TranslateFn, max_chars: int) -> str:
    """Translate a single segment, sentence-splitting if it exceeds the request cap."""
    if len(text) <= max_chars:
        return fn(text, src, tgt)
    pieces = [p for p in _SENTENCE_RE.findall(text) if p.strip()]
    out, cur = [], ""
    for p in pieces:
        if len(cur) + len(p) <= max_chars:
            cur += p
        else:
            if cur:
                out.append(fn(cur, src, tgt))
            cur = p
    if cur:
        out.append(fn(cur, src, tgt))
    return "".join(out)


def _run_batch(texts: List[str], idxs: List[int], results: List[str],
               src: str, tgt: str, fn: TranslateFn, max_chars: int) -> None:
    if len(texts) == 1:
        results[idxs[0]] = _translate_one(texts[0], src, tgt, fn, max_chars)
        return
    joined = _SENTINEL.join(texts)
    translated = fn(joined, src, tgt)
    parts = _SENTINEL_SPLIT_RE.split(translated)
    if len(parts) == len(texts):
        for j, idx in enumerate(idxs):
            results[idx] = parts[j].strip()
    else:
        # Sentinel didn't survive translation -> translate each segment on its own.
        for text, idx in zip(texts, idxs):
            results[idx] = _translate_one(text, src, tgt, fn, max_chars)


def _translate_segments(texts: List[str], src: str, tgt: str,
                        fn: TranslateFn, max_chars: int) -> List[str]:
    results: List[str] = [""] * len(texts)
    batch: List[str] = []
    batch_idx: List[int] = []
    cur = 0

    def flush() -> None:
        nonlocal batch, batch_idx, cur
        if batch:
            _run_batch(batch, batch_idx, results, src, tgt, fn, max_chars)
            batch, batch_idx, cur = [], [], 0

    for i, text in enumerate(texts):
        cost = len(text) + len(_SENTINEL)
        if batch and cur + cost > max_chars:
            flush()
        batch.append(text)
        batch_idx.append(i)
        cur += cost
    flush()
    return results


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def translate_html(html: str, source_lang: str, target_lang: str,
                   translate_fn: TranslateFn, max_chars: int = DEFAULT_MAX_CHARS) -> str:
    """
    Translate the text inside `html` from source_lang to target_lang while
    preserving every HTML tag, <img>, and blank-line paragraph break exactly.
    """
    if not html or not html.strip():
        return html

    parts = _BLOCK_SEP_RE.split(html)  # [block, sep, block, sep, ...]

    # Tokenise each non-separator block into text/tag tokens and collect the jobs.
    tokenised: Dict[int, List[str]] = {}
    jobs: List[tuple] = []  # (part_index, token_index, original_text)
    for pi, part in enumerate(parts):
        if _BLOCK_SEP_RE.fullmatch(part) or not part:
            continue
        tokens = _TAG_RE.split(part)
        tokenised[pi] = tokens
        for ti, tok in enumerate(tokens):
            if not _is_tag(tok) and _is_translatable(tok):
                jobs.append((pi, ti, tok))

    if not jobs:
        return html

    translations = _translate_segments(
        [j[2] for j in jobs], source_lang, target_lang, translate_fn, max_chars
    )
    for (pi, ti, original), translated in zip(jobs, translations):
        tokenised[pi][ti] = _preserve_edge_ws(original, translated)

    return "".join(
        "".join(tokenised[pi]) if pi in tokenised else part
        for pi, part in enumerate(parts)
    )
