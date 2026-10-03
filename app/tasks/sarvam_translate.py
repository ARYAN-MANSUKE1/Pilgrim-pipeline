"""
Translate with Sarvam's chat model (sarvam-105b) instead of Sarvam's Translate API.

Why: the Translate API bills Rs20 per 10,000 characters (~Rs4,600 for the
articles still to redo); the chat model bills per TOKEN (Rs29.28 in / Rs73.20 out
per million), which is a small fraction of that. Same signature as
gemini_translate.translate, so it drops into translate_html / safe_translate,
and every result still goes through safe_translate's checks before it is saved.

A hard spending cap protects the account: once `spent_inr()` reaches the budget
no further request is sent (BudgetExceeded), so a bug or a bigger-than-expected
job cannot run up a bill.
"""

from __future__ import annotations

import re
import threading
import time

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential

from app.config import LANGUAGE_NAMES, settings
from app.tasks.gemini_translate import _SYSTEM  # same devotional-tone / keep-names / native-numerals prompt

URL = "https://api.sarvam.ai/v1/chat/completions"
# NOT plain "sarvam-105b": that one is a reasoning model -- it spends its whole token allowance
# "thinking" (billed as output), returns an empty reply, and takes minutes per call. The
# "-conversations" variant answers directly (0.7s, ~17 tokens for a sentence) at the same price.
MODEL = "sarvam-105b-conversations"
# Rs per token, from https://docs.sarvam.ai/api-reference-docs/pricing (Sarvam 105B).
RATE_IN = 29.28 / 1_000_000
RATE_OUT = 73.20 / 1_000_000


class BudgetExceeded(RuntimeError):
    """The spending cap was reached; nothing more will be sent."""


_lock = threading.Lock()
_use = {"in": 0, "out": 0, "calls": 0}
_budget: float | None = None
# Sarvam's limit is on REQUEST RATE, measured on this key: 2 threads at 4.5 requests/s all
# succeed, 4 threads at 9.2/s get 61 of 92 rejected ("rate_limit_exceeded_error"). Capping
# concurrency alone is not enough -- the sentence-level fallback sends tiny calls that finish
# in ~0.5s, so even 3 at a time is 6+/s. So calls are also spaced: request STARTS are at least
# _MIN_INTERVAL apart across ALL threads (~2.9/s, safely under the ceiling), and any 429 pushes
# every thread back together instead of each sleeping and retrying on its own.
_inflight = threading.Semaphore(4)
_MIN_INTERVAL = 0.35
_COOLDOWN_AFTER_429 = 3.0
_slot_lock = threading.Lock()
_next_slot = 0.0


def _wait_for_slot() -> None:
    global _next_slot
    with _slot_lock:
        now = time.monotonic()
        start = max(now, _next_slot)
        _next_slot = start + _MIN_INTERVAL
    if start > now:
        time.sleep(start - now)


def _push_back_everyone() -> None:
    global _next_slot
    with _slot_lock:
        _next_slot = max(_next_slot, time.monotonic() + _COOLDOWN_AFTER_429)


def set_budget(inr: float | None) -> None:
    global _budget
    _budget = inr


def spent_inr() -> float:
    with _lock:
        return _use["in"] * RATE_IN + _use["out"] * RATE_OUT


def usage() -> dict:
    with _lock:
        return dict(_use)


def _transient(e: BaseException) -> bool:
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code in (408, 429) or e.response.status_code >= 500
    return isinstance(e, httpx.HTTPError)


class EmptyReply(RuntimeError):
    pass


# Short, jittered backoff: a rate-limited call should retry within seconds. (It used to wait up
# to 60s x 6 attempts, which let one stubborn batch stall a whole run for minutes.)
@retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, max=10),
       retry=retry_if_exception(lambda e: _transient(e) or isinstance(e, EmptyReply)), reraise=True)
def translate(text: str, source_lang: str, target_lang: str) -> str:
    if not text or not text.strip():
        return text
    if _budget is not None and spent_inr() >= _budget:
        raise BudgetExceeded(f"spent Rs{spent_inr():.2f} of the Rs{_budget:.0f} budget")
    if not settings.sarvam_api_key:
        raise RuntimeError("SARVAM_API_KEY is not set")
    src, tgt = LANGUAGE_NAMES.get(source_lang, source_lang), LANGUAGE_NAMES.get(target_lang, target_lang)
    with _inflight:
        _wait_for_slot()
        r = httpx.post(
            URL, timeout=240, headers={"api-subscription-key": settings.sarvam_api_key},
            json={"model": MODEL, "temperature": 0.3, "max_tokens": 6000,
                  "messages": [{"role": "system", "content": _SYSTEM.format(target=tgt)},
                               {"role": "user", "content": f"Translate this from {src} to {tgt}:\n\n{text}"}]})
    if r.status_code == 429:
        _push_back_everyone()
    r.raise_for_status()
    d = r.json()
    u = d.get("usage") or {}
    with _lock:   # counted even if the reply turns out unusable: the tokens were billed
        _use["in"] += int(u.get("prompt_tokens") or 0)
        _use["out"] += int(u.get("completion_tokens") or 0)
        _use["calls"] += 1
    out = ((d.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    out = re.sub(r"(?s)<think>.*?</think>", "", out).strip()   # drop any reasoning trace
    if not out:
        raise EmptyReply("Sarvam returned an empty reply")
    return out
