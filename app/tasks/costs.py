"""
Per-temple cost ledger.

Nothing recorded usage before this module existed, so cost is measured only for
work done from now on: every Gemini call logs its token counts, every Sarvam
call logs the characters actually sent. Rows are appended to a JSONL ledger at
the repo root; the dashboard's CSV export sums them per temple.

Temples processed earlier have no rows at all -- for those, estimate() falls
back to the measured per-language averages from full-site-cost.pdf, and the
export marks the row "estimated".

The in-flight temple is a ContextVar, so several temples can be processed at
once without their costs cross-attributing. Every thread pool that does billable
work must submit through contextvars.copy_context().run, or the worker thread's
temple will not be visible inside the pool (see dashboard/pipeline.py).
"""

from __future__ import annotations

import contextvars
import json
import threading
from pathlib import Path

from app.config import settings

LEDGER = Path(__file__).resolve().parents[2] / "cost_ledger.jsonl"

_lock = threading.Lock()
# ContextVar, not a plain global: two temples run concurrently (jobs.py spawns
# several workers), and a global would bill one temple's audio to the other.
_current: contextvars.ContextVar[int | None] = contextvars.ContextVar("temple_id", default=None)

# Measured per-temple INR averages from full-site-cost.pdf (Bulbul v2 audio,
# 107 fully-processed temples; bn/pa projected from a sample). Used ONLY as the
# fallback for temples processed before cost logging existed.
PDF_EST = {  # lang: (translation_inr, audio_inr)
    "en": (2.13, 8.82), "ta": (2.04, 8.43), "ml": (1.94, 8.01), "pa": (1.91, 7.90),
    "hi": (1.80, 7.43), "te": (1.78, 7.37), "bn": (1.73, 7.14), "kn": (1.72, 7.13),
    "gj": (1.59, 6.58), "mr": (0.00, 7.50),
}


def set_temple(temple_id: int | None) -> None:
    """Attribute every cost recorded in THIS context to this temple (None = off)."""
    _current.set(temple_id)


def _append(row: dict) -> None:
    """Best-effort -- a ledger write must never break a pipeline run."""
    try:
        with _lock:
            with LEDGER.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def audio_inr(chars: int) -> float:
    """Sarvam bills per character; v3 is 2x the v2 rate."""
    rate = settings.sarvam_inr_per_10k_chars * (2.0 if "v3" in settings.sarvam_model else 1.0)
    return chars * rate / 10_000


def translation_inr(in_tokens: int, out_tokens: int) -> float:
    return (in_tokens * settings.gemini_usd_per_1m_input
            + out_tokens * settings.gemini_usd_per_1m_output) / 1_000_000 * settings.usd_inr


def record_audio(lang: str, chars: int) -> None:
    tid = _current.get()
    if tid is None or chars <= 0:
        return
    _append({"temple_id": tid, "kind": "audio", "lang": lang,
             "units": chars, "inr": round(audio_inr(chars), 4)})


def record_translation(usage: dict | None, lang: str = "") -> None:
    """Log one Gemini call from its response usageMetadata."""
    tid = _current.get()
    if tid is None or not usage:
        return
    in_tok = int(usage.get("promptTokenCount") or 0)
    # thoughtsTokenCount is reported SEPARATELY from candidatesTokenCount but is
    # billed at the output rate ("Output price (including thinking tokens)").
    # Omitting it once hid 58% of a real bill -- always add it in.
    out_tok = (int(usage.get("candidatesTokenCount") or 0)
               + int(usage.get("thoughtsTokenCount") or 0))
    if not (in_tok or out_tok):
        return
    _append({"temple_id": tid, "kind": "translation", "lang": lang,
             "units": in_tok + out_tok, "inr": round(translation_inr(in_tok, out_tok), 4)})


def totals() -> dict[int, dict[str, float]]:
    """{temple_id: {"translation": inr, "audio": inr}} over the whole ledger."""
    out: dict[int, dict[str, float]] = {}
    if not LEDGER.exists():
        return out
    with LEDGER.open(encoding="utf-8") as f:
        for line in f:
            try:
                row = json.loads(line)
                t = out.setdefault(int(row["temple_id"]), {"translation": 0.0, "audio": 0.0})
                t[row["kind"]] = t.get(row["kind"], 0.0) + float(row["inr"])
            except Exception:
                continue  # a truncated last line (crash mid-write) shouldn't lose the rest
    return out


def estimate(text_langs, audio_langs, source: str = "") -> dict[str, float]:
    """PDF-average fallback for temples processed before cost logging existed."""
    tr = sum(PDF_EST.get(l, (0.0, 0.0))[0] for l in text_langs if l != source)
    au = sum(PDF_EST.get(l, (0.0, 0.0))[1] for l in audio_langs)
    return {"translation": round(tr, 2), "audio": round(au, 2)}


if __name__ == "__main__":  # self-check: python -m app.tasks.costs
    assert round(audio_inr(10_000), 2) == 15.0, audio_inr(10_000)          # PDF rate
    assert round(translation_inr(1_000_000, 0), 2) == round(settings.gemini_usd_per_1m_input * settings.usd_inr, 2)
    e = estimate(["mr", "en", "hi"], ["mr", "en"], source="mr")
    assert e == {"translation": round(2.13 + 1.80, 2), "audio": round(7.50 + 8.82, 2)}, e
    set_temple(None)
    record_audio("en", 5000)  # must be a no-op, not a crash, with no temple set

    # two concurrent "temples" must not bill each other
    import threading as _th
    seen = {}

    def _worker(tid):
        set_temple(tid)
        seen[tid] = _current.get()

    ts = [_th.Thread(target=_worker, args=(i,)) for i in (111, 222)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert seen == {111: 111, 222: 222}, seen
    assert _current.get() is None, "a child thread must not leak into the parent"
    print("costs self-check OK")
