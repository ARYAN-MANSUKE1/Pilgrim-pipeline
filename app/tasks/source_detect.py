"""
Pick the source-language field for a temple, and decide which fields to fill.

The source language varies per temple: most are Marathi, some English, a few
Hindi. The remaining language fields are empty or hold a short placeholder until
the pipeline fills them. So the orchestrator can't assume a fixed source — it
must look at the actual fields and translate FROM the populated one.

Rule (as agreed):
  - Measure VISIBLE TEXT length per candidate field (HTML tags + <img> stripped),
    so a lone image or a "coming soon" stub does NOT count as real content.
  - The source is the candidate field that clears `min_chars`.
  - If two or more candidates clear it (e.g. a temple already has both a real
    source and an earlier machine translation), that's returned as `ambiguous`
    so the caller can apply a configured priority or skip + alert — never a
    silent guess.

Only mr/en/hi are ever human-authored originals; gu/ta/te are always generated,
so they're not source candidates by default.

Pure stdlib -> unit-testable with no API/WordPress.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# Human-authored originals only ever live in these fields.
DEFAULT_SOURCE_CANDIDATES: Sequence[str] = ("mr", "en", "hi")
# When several fields are populated, prefer the source in this order (team decision).
DEFAULT_SOURCE_PRIORITY: Sequence[str] = ("mr", "en", "hi")
# A real temple body is thousands of chars; placeholders/titles are short.
DEFAULT_MIN_CHARS = 200


def visible_text_length(html: Optional[str]) -> int:
    """Length of human-visible text: HTML tags and <img> removed, whitespace collapsed."""
    if not html:
        return 0
    text = _TAG_RE.sub(" ", html)
    text = _WS_RE.sub(" ", text).strip()
    return len(text)


@dataclass
class SourceResult:
    source: Optional[str]          # chosen source lang, or None if nothing qualifies
    lengths: Dict[str, int]        # visible-text length per candidate
    qualified: List[str]           # candidates that cleared min_chars, best first
    ambiguous: bool                # True if >1 candidate cleared min_chars


def detect_source_language(
    fields: Dict[str, Optional[str]],
    candidates: Sequence[str] = DEFAULT_SOURCE_CANDIDATES,
    min_chars: int = DEFAULT_MIN_CHARS,
    priority: Optional[Sequence[str]] = DEFAULT_SOURCE_PRIORITY,
) -> SourceResult:
    """
    Choose the source language for a temple from its language fields.

    `fields` maps lang code -> HTML content (missing/None allowed).
    `priority` orders tie-breaking when several fields qualify; defaults to
    mr > en > hi (team decision). Pass priority=None to fall back to longest-wins.
    """
    lengths = {lang: visible_text_length(fields.get(lang)) for lang in candidates}
    qualified = [lang for lang in candidates if lengths[lang] >= min_chars]

    if priority:
        rank = {lang: i for i, lang in enumerate(priority)}
        qualified.sort(key=lambda l: (rank.get(l, len(priority)), -lengths[l]))
    else:
        qualified.sort(key=lambda l: lengths[l], reverse=True)

    return SourceResult(
        source=qualified[0] if qualified else None,
        lengths=lengths,
        qualified=qualified,
        ambiguous=len(qualified) > 1,
    )


def pick_source(fields: Dict[str, Optional[str]]) -> Optional[str]:
    """The language to translate FROM: Marathi > English > Hindi when any of them has
    an article; otherwise the longest article in any other language. That second step
    is for temples added in, say, Tamil ("Other" on Add Temple): without it they had
    "no article to translate from" and could never be re-run or counted."""
    return (detect_source_language(fields).source
            or detect_source_language(fields, candidates=tuple(fields), priority=None).source)
