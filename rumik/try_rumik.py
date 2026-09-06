"""
Rumik Silk TTS - standalone trial, deliberately outside the pipeline.

Generates audio for a real temple so it can be compared against the Sarvam
recording already on staging for the same temple and language. Nothing here is
imported by the pipeline; app/tasks/audio.py is untouched until Rumik is chosen.

Reuses the pipeline's own chunker and WAV stitcher so the comparison is fair --
same text preparation, same joining, only the vendor differs.

Setup:  put RUMIK_API_KEY=rk_live_... in .env

    python rumik/try_rumik.py 26445 mr en ta          # one temple, three languages
    python rumik/try_rumik.py 26445 mr --model mulberry --speaker siya

Writes rumik/out/<temple>_<lang>_<model>.wav and prints Rumik's own billed cost
from the X-Usage-Cost-Nanos response header.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings                      # noqa: E402
from app.tasks import wp_client as wp                # noqa: E402
from app.tasks.audio import _stitch_wav, chunk_text  # noqa: E402
from app.tasks.structured_translate import strip_tags  # noqa: E402

API = "https://silk-api.rumik.ai/v1/tts"

# Per-language voice descriptions. The accent value must match the language --
# these are the accents Rumik documents for Indian voices.
_ACCENT = {"mr": "marathi", "hi": "hindi", "gj": "gujarati", "ta": "south_indian",
           "te": "telugu", "ml": "malayali", "kn": "kannada", "bn": "bengali",
           "pa": "punjabi", "en": "indian"}
DEFAULT_DESC = {
    l: (f"a female 30s {a} voice, normal pitch, smooth timbre, brisk pacing, "
        f"warm, reverent register, like a devotional narrator.")
    for l, a in _ACCENT.items()
}
MAX_CHARS = 2000          # Rumik's documented per-request cap (Sarvam allowed 2500)
OUT = Path(__file__).parent / "out"


def _key() -> str:
    key = os.environ.get("RUMIK_API_KEY", "")
    if not key:  # settings ignores unknown .env keys, so read the file directly
        for line in (Path(__file__).resolve().parents[1] / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("RUMIK_API_KEY="):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("RUMIK_API_KEY not set - add it to .env")
    return key


def synth(text: str, model: str, speaker: str | None, description: str | None,
          lang: str = "") -> tuple[bytes, int, float]:
    """One chunk -> (wav bytes, duration ms, cost in rupees)."""
    body = {"text": text, "model": model, "_lang": lang}
    if model == "mulberry":
        # mulberry requires a description; speaker is optional on top of it
        # Mulberry is a described-voice model: the accent and pacing come from this
        # sentence, not from the text's language. Their guide's format is
        #   "a {gender} {age} {accent} voice, {pitch} pitch, {timbre}, {pacing}
        #    pacing, {emotion}, {register} register, like a {role}."
        # A generic English description produced English-accented Marathi at a
        # crawl -- the accent must be named per language, and pacing set.
        body["description"] = description or DEFAULT_DESC.get(
            body.get("_lang", ""), "a female 30s indian voice, normal pitch, smooth timbre, "
            "brisk pacing, warm, reverent register, like a devotional narrator.")
        if speaker:
            body["speaker"] = speaker
    body.pop("_lang", None)          # internal only, not an API field
    r = httpx.post(API, json=body, timeout=300,
                   headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    ms = int(r.headers.get("X-Audio-Duration-Ms") or 0)
    nanos = int(r.headers.get("X-Usage-Cost-Nanos") or 0)
    return r.content, ms, nanos / 1e9


def main() -> None:
    # strip flags AND their values -- a bare positional filter treated
    # "--model mulberry" as the language "mulberry"
    argv, args = sys.argv[1:], []
    i = 0
    while i < len(argv):
        if argv[i].startswith("--"):
            i += 2
            continue
        args.append(argv[i])
        i += 1
    if not args:
        sys.exit(__doc__)
    temple_id, langs = int(args[0]), (args[1:] or ["mr"])
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "muga"
    speaker = sys.argv[sys.argv.index("--speaker") + 1] if "--speaker" in sys.argv else None
    desc = sys.argv[sys.argv.index("--description") + 1] if "--description" in sys.argv else None
    # --chars N : cap the text per language. Rumik's free allowance is 2000
    # characters total, so a full 5,400-char article cannot be trialled for free.
    cap = int(sys.argv[sys.argv.index("--chars") + 1]) if "--chars" in sys.argv else None

    OUT.mkdir(exist_ok=True)
    wp.refresh_language_fields()
    base = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
    post = httpx.get(f"{base}/temple/{temple_id}", params={"context": "edit"},
                     auth=(settings.wp_user, settings.wp_app_password), timeout=180).json()
    acf = post.get("acf") or {}
    print(f"temple {temple_id}: {(post.get('title') or {}).get('rendered','')[:60]}")
    print(f"model={model}" + (f" speaker={speaker}" if speaker else "") + f"  chunk<= {MAX_CHARS}\n")

    total_cost = total_ms = 0.0
    for lang in langs:
        field = wp.CONTENT_FIELD_KEYS.get(lang)
        text = strip_tags(acf.get(field) or "") if field else ""
        if not text.strip():
            print(f"  {lang}: no content on staging, skipped")
            continue
        if cap:
            text = text[:cap].rsplit(".", 1)[0] + "."   # trim to a sentence end
        chunks = chunk_text(text, max_chars=MAX_CHARS)
        wavs, cost, ms = [], 0.0, 0
        t0 = time.time()
        for i, c in enumerate(chunks, 1):
            try:
                w, d, rs = synth(c, model, speaker, desc, lang)
            except Exception as e:  # noqa: BLE001 - one language failing shouldn't stop the rest
                print(f"  {lang}: chunk {i}/{len(chunks)} FAILED: {e}")
                wavs = []
                break
            wavs.append(w); cost += rs; ms += d
        if not wavs:
            continue
        out = OUT / f"{temple_id}_{lang}_{model}.wav"
        out.write_bytes(_stitch_wav(wavs))
        total_cost += cost; total_ms += ms
        print(f"  {lang}: {len(text):>6,} chars -> {len(chunks)} req, {ms/60000:>4.1f} min audio, "
              f"Rs {cost:>6.3f}, {time.time()-t0:>5.1f}s  -> {out.name}")

    if total_ms:
        print(f"\ntotal: {total_ms/60000:.1f} min audio, Rs {total_cost:.2f}")
        print(f"Sarvam v3 for the same characters would be about "
              f"Rs {sum(len(strip_tags(acf.get(wp.CONTENT_FIELD_KEYS[l]) or '')) for l in langs if wp.CONTENT_FIELD_KEYS.get(l)) * 30 / 10000:.2f}")
    print(f"\ncompare against the Sarvam audio already on staging:")
    for lang in langs:
        f = wp.AUDIO_FIELD_KEYS.get(lang)
        if f and acf.get(f):
            m = httpx.get(f"{base}/media/{acf[f]}", auth=(settings.wp_user, settings.wp_app_password), timeout=120).json()
            print(f"  {lang}: {m.get('source_url')}")


if __name__ == "__main__":
    main()
