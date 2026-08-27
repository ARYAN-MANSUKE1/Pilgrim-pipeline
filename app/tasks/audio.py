"""
Audio task — turns temple text into a single audio file and stores it on Cloudflare R2.

Pipeline per language:
    text -> chunk (<=1500 chars, sentence-aware)
         -> Sarvam Bulbul v2 TTS per chunk (WAV, with retry)
         -> stitch chunks into one WAV (stdlib `wave`, no ffmpeg needed)
         -> (optional) compress to MP3 if ffmpeg is available
         -> upload to R2
         -> return public CDN URL

Sarvam v2 caps each request at 1500 characters, so longer temple descriptions
(avg ~4,650, longest ~14,700) are split and stitched back together.
"""

import base64
import io
import logging
import re
import shutil
from pathlib import Path
import subprocess
import unicodedata
import wave
from typing import Dict, List, Tuple

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import LANGUAGE_CODES, settings
from app.tasks import costs
from app.tasks import tts_normalize as tts_norm
from app.tasks.tts_normalize import expand_abbreviations

logger = logging.getLogger(__name__)

# Split on sentence boundaries: Devanagari danda (।), full stop, ! ? and newlines.
_SENTENCE_RE = re.compile(r"[^।.!?\n]*[।.!?\n]|[^।.!?\n]+")

# Pause (ms) inserted between stitched chunks so sentence joins sound natural.
_CHUNK_PAUSE_MS = 120


# ---------------------------------------------------------------------------
# Text chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, max_chars: int | None = None) -> List[str]:
    """Split text into <= max_chars pieces, breaking on sentence boundaries."""
    max_chars = max_chars or settings.tts_max_chars
    text = (text or "").strip()
    if not text:
        return []

    # Keep track of which matches ended on a bare newline (heading/paragraph
    # break) rather than real punctuation -- .strip() below would otherwise
    # throw that newline away, and every sentence gets rejoined with a plain
    # space, so a title line runs straight into the next line with NO
    # separator at all (this is what glued "...Temple" directly onto
    # "Budhwar Peth..." with no pause, and Sarvam read it as one run-on).
    # Insert a period in its place so TTS actually pauses between lines.
    sentences = []
    for raw in _SENTENCE_RE.findall(text):
        s = raw.strip()
        if not s:
            continue
        if raw.rstrip(" \t").endswith("\n") and not re.search(r"[।.!?]$", s):
            s += "."
        sentences.append(s)
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        # A single sentence longer than the limit is hard-split.
        while len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:max_chars])
            sentence = sentence[max_chars:]

        if not sentence:
            continue
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# Latin script -> Devanagari, for TTS only
# ---------------------------------------------------------------------------
#
# The English content stores Indian proper nouns romanised ("Shrimant
# Dagadusheth Halwai Ganapati", "Budhwar Peth", "Pune"). Sarvam's en-IN voice
# applies ENGLISH phonetics to those, so temple names -- the whole point of the
# site -- come out garbled ("Pune" read as "Pun"). They are scattered through
# the body text, not just the heading, so there is no structural subset to
# patch: the entire string has to be handed to the voice in Devanagari.
#
# Sarvam's own transliterate API does it, and mr-IN is the correct target, NOT
# hi-IN: mr-IN reproduces the names byte-identical to the site's Marathi source
# field (श्रीमंत दगडूशेठ), while hi-IN mangles them (श्रीमान् दागदशुशेथ).
# English words come back as होल्ड्स / सिग्निफिकंट etc. and read correctly.
#
# Names are only ever SCRIPT-CONVERTED here, never re-spelled or guessed at,
# and nothing written to WordPress is touched -- this rewrites the string on
# its way to the speech API only.
#
# Applies to any predominantly-Latin text (today: English). Languages that
# already carry their names in a native script -- Tamil, Telugu, Kannada,
# Bengali, ... -- are detected as non-Latin and skipped entirely, so they cost
# nothing extra and are left exactly as they are.

_TRANSLITERATE_URL = "https://api.sarvam.ai/transliterate"
_TRANSLITERATE_MAX_CHARS = 1000   # hard API cap (verified against the live API, 2026-08-06)

# "Letter" in the Unicode sense (excludes digits/underscore/punctuation).
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)


def _is_latin_script(text: str) -> bool:
    """True if most letters are A-Z/a-z — i.e. the text needs transliterating."""
    letters = _LETTER_RE.findall(text)
    if not letters:
        return False
    latin = sum(1 for c in letters if "a" <= c.lower() <= "z")
    return latin / len(letters) > 0.5


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception_type((httpx.HTTPError,)),
    reraise=True,
)
def _transliterate_chunk(text: str) -> str:
    payload = {
        "input": text,
        "source_language_code": "en-IN",
        "target_language_code": "mr-IN",
        # numerals_format=international + spoken_form=False keeps "1893" as the
        # digits "1893" so the en-IN voice reads it as English ("eighteen
        # ninety-three"). Both alternatives are wrong here:
        #   spoken_form=True    -> expands it to MARATHI words (अठराशे त्र्याण्णव)
        #                          in the middle of English narration, and also
        #                          mangles possessives ("Pune's" -> पुणे स).
        #   numerals_format=native -> writes Devanagari digits (१८९३).
        # Every other language skips transliteration entirely, so its numbers
        # stay in its own source script and its own voice reads them natively --
        # Hindi numbers in Hindi, Marathi in Marathi.
        "numerals_format": "international",
        "spoken_form": False,
    }
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }
    resp = httpx.post(_TRANSLITERATE_URL, json=payload, headers=headers, timeout=45)
    resp.raise_for_status()
    return resp.json().get("transliterated_text") or text


def to_devanagari(text: str) -> str:
    """
    Romanised text -> Devanagari, for speech only.

    Chunked to the API's 1000-char cap on sentence boundaries (reusing
    chunk_text) so no word is ever split across two requests. A chunk that
    fails falls back to its original romanised text rather than aborting:
    slightly-worse pronunciation for that stretch beats losing the whole
    file, matching how a single language's failure is isolated elsewhere.
    """
    parts = chunk_text(text, max_chars=_TRANSLITERATE_MAX_CHARS)
    out: List[str] = []
    for i, part in enumerate(parts, 1):
        try:
            out.append(_transliterate_chunk(part))
        except Exception as e:
            logger.warning("Transliteration failed for part %d/%d (%s) — leaving it romanised.", i, len(parts), e)
            out.append(part)
    return " ".join(out)


# ---------------------------------------------------------------------------
# Numbers -> spoken words, in the language being narrated
# ---------------------------------------------------------------------------
#
# Sarvam's TTS reads a bare number digit-by-digit AND in English, so "१८९३" in
# Marathi narration came out as "one eight nine three". Each language has to be
# handed its numbers already spelled out in its own words.
#
#   English  -> done locally (source==target transliteration is a no-op there).
#   Indic    -> Sarvam transliterate with source==target and spoken_form=True,
#               which is context-aware and gets cases hand-written rules would
#               not: 5:30 -> "संध्याकाळी साडेपाच वाजता", 7.5 -> "सात दशांश पाच".
#
# Only the NUMBERS are sent, not the whole text -- a few dozen characters per
# temple instead of a few thousand, so the added cost is negligible for the
# nine Indic languages (full-text transliteration for all of them would have
# cost more than the TTS itself).
#
# Long digit runs and leading-zero groups (phone numbers, STD codes) are left
# alone deliberately: digit-by-digit is the CORRECT reading for those, and
# spelling "24496464" out as a cardinal would be nonsense.

_PHONE_MIN_DIGITS = 7


def _is_phone_like(token: str) -> bool:
    digits = re.sub(r"\D", "", _ascii_digits(token))
    return len(digits) >= _PHONE_MIN_DIGITS or (len(digits) > 1 and digits[0] == "0")


def _ascii_digits(s: str) -> str:
    """
    Devanagari (and any other Indic) digits -> ASCII, for the API call only.

    Required: given Devanagari input, Sarvam reads the comma between two
    numbers as a THOUSANDS separator -- "५, ३०" came back as the single value
    पाच हजार तीनशे (5,300) instead of "पाच" and "तीस". The identical request in
    ASCII digits returns them correctly as two values. The original token is
    kept for substituting back into the text, so nothing on the page changes.
    """
    return "".join(str(unicodedata.digit(c)) if c.isdigit() else c for c in s)


def _for_api(token: str) -> str:
    """
    Token as sent to Sarvam: ASCII digits, grouping commas KEPT.

    The commas have to stay -- Sarvam reads the magnitude off them, and gets
    it materially wrong without: "1,68,864" -> एक लाख अडुसष्ट हजार आठशे चौसष्ट
    (correct), but "168864" -> एक लाख अठ्ठ्याहत्तर हजार सहाशे चौसष्ट, which is
    178,664 -- a different number entirely. "16,000" is सोळा हजार, "16000"
    comes back as सोळाशे (1,600).

    Because the batch is itself comma-separated, a token containing a comma
    cannot be batched; _spoken_map sends those individually.
    """
    return _ascii_digits(token)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception_type((httpx.HTTPError,)),
    reraise=True,
)
def _transliterate_spoken(text: str, sarvam_lang: str) -> str:
    """Raw spoken-form expansion of `text` (numbers -> words) in `sarvam_lang`."""
    payload = {
        "input": text,
        "source_language_code": sarvam_lang,
        "target_language_code": sarvam_lang,
        "numerals_format": "international",
        "spoken_form": True,
    }
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }
    resp = httpx.post(_TRANSLITERATE_URL, json=payload, headers=headers, timeout=45)
    resp.raise_for_status()
    return (resp.json().get("transliterated_text") or "").strip()


def _spoken_numbers(tokens: List[str], sarvam_lang: str) -> List[str]:
    """Batch-expand comma-free number tokens. One request, split on the comma."""
    return [p.strip() for p in _transliterate_spoken(", ".join(tokens), sarvam_lang).split(",")]


_SPOKEN_CACHE: Dict[Tuple[str, str], str] = {}


def _spoken_map(tokens: List[str], sarvam_lang: str) -> Dict[str, str]:
    """
    token -> spoken words, batched, cached, with a per-token retry.

    Sarvam sometimes SILENTLY DROPS an entry from a batch -- sending
    [1893, 1892, 1894, 1896, 1968, ...] came back without 1896 at all, 11 in
    and 10 out. Trusting that response would have mapped every later number
    onto the wrong words, so a mismatch has to fall back rather than be used.
    Falling back for the WHOLE text was too blunt though: one dropped token
    left every number in the temple as bare digits, read out in English.

    So: try the batch (1 request); if the count is off, re-request the tokens
    one at a time, and keep whatever succeeds. Anything still unresolved is
    simply left as digits -- degraded for that one number, not for the page.

    Cached across temples for the whole process: years repeat constantly
    (1893, 1968, ...), so a bulk run resolves most numbers without any request.
    """
    todo = [t for t in dict.fromkeys(tokens) if (sarvam_lang, t) not in _SPOKEN_CACHE]

    def resolve_alone(t: str) -> None:
        """One request for one token; the whole reply is the answer, unsplit."""
        try:
            got = _transliterate_spoken(_for_api(t), sarvam_lang)
        except Exception as e:
            logger.warning("Could not expand %r for %s (%s) — leaving digits.", t, sarvam_lang, e)
            return
        if got:
            _SPOKEN_CACHE[(sarvam_lang, t)] = got
        else:
            logger.warning("Sarvam gave no expansion for %r on %s — leaving digits.", t, sarvam_lang)

    # A token with a grouping comma can't ride in a comma-separated batch.
    batchable = [t for t in todo if "," not in _for_api(t)]
    for t in (t for t in todo if "," in _for_api(t)):
        resolve_alone(t)

    if batchable:
        parts: List[str] = []
        try:
            parts = _spoken_numbers([_for_api(t) for t in batchable], sarvam_lang)
        except Exception as e:
            logger.warning("Number expansion request failed for %s (%s).", sarvam_lang, e)

        if len(parts) == len(batchable) and all(parts):
            _SPOKEN_CACHE.update({(sarvam_lang, t): p for t, p in zip(batchable, parts)})
        else:
            logger.info("Batch returned %d for %d token(s) on %s — retrying individually.",
                        len(parts), len(batchable), sarvam_lang)
            for t in batchable:
                resolve_alone(t)

    return {t: _SPOKEN_CACHE[(sarvam_lang, t)] for t in tokens if (sarvam_lang, t) in _SPOKEN_CACHE}


def _atoms(token: str) -> List[str]:
    """
    The pieces a token is expanded as.

    A clock time is split so hour and minute are expanded as PLAIN numbers.
    Handing "5:30" to Sarvam whole makes it invent a time of day and a
    "o'clock" ("संध्याकाळी साडेपाच वाजता" — evening half-past-five), which
    then contradicts the सकाळी/सुबह ("morning") already in the sentence and
    duplicates its वाजल्यापासून. Expanding "5" and "30" separately keeps the
    sentence's own wording authoritative.

    A decimal is NOT split: Sarvam reads "7.5" correctly as "सात दशांश पाच",
    whereas splitting would give the wrong "सात पाच" (seven five).
    """
    for sep in (":", "."):
        if sep in token:
            hour, _, minute = token.partition(sep)
            # Only a bare clock time splits. A "." with a ONE-digit fraction is
            # a measurement (१.५ किमी) and must stay whole, or it would be read
            # as "one thirty" instead of "one point five". A time carrying a
            # glued case ending ("5:30ಕ್ಕೆ") also stays whole for Sarvam to
            # inflect, and int() would raise on it anyway.
            if hour.isdigit() and minute.isdigit() and tts_norm._is_clock(hour, minute):
                return [hour] if int(minute) == 0 else [hour, minute]
            break
    return [token]


def expand_numbers(text: str, lang: str) -> str:
    """Replace every number in `text` with its spoken form in `lang`."""
    # English matches digits only; the Indic languages also take any case
    # ending glued onto them, which Sarvam needs in order to inflect the
    # spelled-out number correctly (see NUMBER_WITH_SUFFIX_RE).
    pattern = tts_norm.NUMBER_RE if lang == "en" else tts_norm.NUMBER_WITH_SUFFIX_RE
    tokens = [t for t in dict.fromkeys(pattern.findall(text)) if not _is_phone_like(t)]
    if not tokens:
        return text

    if lang == "en":
        spoken = {t: tts_norm.english_number_phrase(t) for t in tokens}
    else:
        sarvam_lang = LANGUAGE_CODES.get(lang)
        if not sarvam_lang:
            return text
        atoms = list(dict.fromkeys(a for t in tokens for a in _atoms(t)))
        amap = _spoken_map(atoms, sarvam_lang)
        # Keep only tokens whose every piece resolved; any that didn't stays as
        # digits, so one unresolved number never silences the rest.
        spoken = {
            t: " ".join(amap[a] for a in _atoms(t))
            for t in tokens
            if all(a in amap for a in _atoms(t))
        }
        if not spoken:
            return text

    # Longest first, so "1893" is never partially rewritten by a match on "189".
    for tok in sorted(spoken, key=len, reverse=True):
        text = re.sub(rf"(?<!\d){re.escape(tok)}(?!\d)", spoken[tok], text)
    return text


# ---------------------------------------------------------------------------
# Sarvam TTS (one chunk -> WAV bytes)
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception_type((httpx.HTTPError,)),
    reraise=True,
)
def _synthesize_chunk(text: str, lang_code: str) -> List[bytes]:
    """
    Call Sarvam for one chunk; return ALL WAV segments it produces.

    Sarvam internally splits the input (~every 250-300 chars) and returns one
    entry per segment in the response "audios" array. We must keep every entry —
    using only audios[0] silently truncates the output.
    """
    payload = {
        "text": text,
        "target_language_code": lang_code,
        "model": settings.sarvam_model,
        "speaker": settings.tts_speaker,
        "pace": settings.tts_pace,
        "speech_sample_rate": settings.tts_sample_rate,
        "output_audio_codec": "wav",
        "enable_preprocessing": settings.tts_enable_preprocessing,
    }
    # Bulbul v3 rejects pitch/loudness (uses different expressive controls); only send them for v2.
    if "v3" not in settings.sarvam_model:
        payload["pitch"] = settings.tts_pitch
        payload["loudness"] = settings.tts_loudness
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }
    resp = httpx.post(settings.sarvam_tts_url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()

    audios = resp.json().get("audios") or []
    if not audios:
        raise RuntimeError(f"Sarvam returned no audio (lang={lang_code})")
    return [base64.b64decode(a) for a in audios]


# ---------------------------------------------------------------------------
# Stitch WAV chunks (stdlib `wave` — no ffmpeg / pydub / audioop)
# ---------------------------------------------------------------------------

def _stitch_wav(wav_chunks: List[bytes], pause_ms: int = _CHUNK_PAUSE_MS) -> bytes:
    """Concatenate same-format WAV chunks into one WAV, with short pauses between."""
    if len(wav_chunks) == 1 and pause_ms == 0:
        return wav_chunks[0]

    with wave.open(io.BytesIO(wav_chunks[0]), "rb") as first:
        nchannels = first.getnchannels()
        sampwidth = first.getsampwidth()
        framerate = first.getframerate()

    silence = b"\x00" * int(nchannels * sampwidth * framerate * (pause_ms / 1000.0))

    out = io.BytesIO()
    with wave.open(out, "wb") as writer:
        writer.setnchannels(nchannels)
        writer.setsampwidth(sampwidth)
        writer.setframerate(framerate)
        for i, chunk in enumerate(wav_chunks):
            with wave.open(io.BytesIO(chunk), "rb") as reader:
                writer.writeframes(reader.readframes(reader.getnframes()))
            if i < len(wav_chunks) - 1 and silence:
                writer.writeframes(silence)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Optional MP3 compression (uses ffmpeg if present; else keeps WAV)
# ---------------------------------------------------------------------------

def _ffmpeg() -> str | None:
    """Locate ffmpeg. PATH first, then winget's install dir -- a winget install
    only reaches PATH after a shell restart, so relying on PATH alone silently
    kept the pipeline on WAV (21MB uploads) long after ffmpeg was available."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    for p in Path.home().glob("AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg*/**/ffmpeg.exe"):
        return str(p)
    return None


def _encode_mp3(wav_bytes: bytes) -> bytes | None:
    """Convert WAV -> MP3 via ffmpeg. Returns None if ffmpeg is unavailable."""
    exe = _ffmpeg()
    if not exe:
        return None
    proc = subprocess.run(
        [exe, "-hide_banner", "-loglevel", "error",
         # 64k mono: Sarvam returns 22050 Hz mono speech, which is the easiest
         # possible material to compress -- 64k is the standard podcast bitrate
         # for it and is transparent here. 128k doubled the file for no audible
         # gain. Measured: 13.8MB WAV -> 2.5MB MP3, duration identical.
         "-i", "pipe:0", "-f", "mp3", "-ac", "1", "-b:a", "64k", "pipe:1"],
        input=wav_bytes, capture_output=True,
    )
    if proc.returncode != 0 or not proc.stdout:
        logger.warning("ffmpeg mp3 encode failed; keeping WAV. %s", proc.stderr.decode("utf-8", "ignore")[:200])
        return None
    return proc.stdout


# ---------------------------------------------------------------------------
# Public: text -> audio bytes
# ---------------------------------------------------------------------------

def synthesize(text: str, lang: str) -> Tuple[bytes, str]:
    """
    Full text -> single audio file.
    Returns (audio_bytes, ext) where ext is "mp3" (if ffmpeg present) or "wav".
    """
    lang_code = LANGUAGE_CODES.get(lang)
    if not lang_code:
        raise ValueError(f"Unsupported language: {lang}")

    text = expand_abbreviations(text, lang)   # ता./जि. -> तालुका/जिल्हा etc. for correct speech
    # Numbers -> words in THIS language, before any transliteration, so English
    # gets English words ("eighteen ninety-three") that then convert to
    # Devanagari as ordinary words instead of surviving as bare digits.
    text = expand_numbers(text, lang)
    # Romanised text (English) -> Devanagari so temple names are pronounced as
    # written on the site instead of being read with English phonetics.
    # Runs AFTER expand_abbreviations so expanded words get converted too.
    if _is_latin_script(text):
        logger.info("Transliterating romanised text to Devanagari for lang=%s", lang)
        text = to_devanagari(text)
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No text to synthesize")

    logger.info("Synthesizing %d chunk(s) for lang=%s", len(chunks), lang)
    stitched_chunks: List[bytes] = []
    for i, chunk in enumerate(chunks, 1):
        segments = _synthesize_chunk(chunk, lang_code)
        costs.record_audio(lang, len(chunk))  # Sarvam bills per character sent
        # Segments here are Sarvam's OWN internal re-split of a single
        # sentence-safe chunk -- those cut points aren't word-aware (this is
        # what clipped "Pune" into "Pun" + gap + "e"), so join them with NO
        # pause. The pause belongs only between OUR chunks, below.
        stitched_chunks.append(_stitch_wav(segments, pause_ms=0))
        logger.info("  chunk %d/%d done (%d chars, %d segment(s))", i, len(chunks), len(chunk), len(segments))

    wav = _stitch_wav(stitched_chunks)
    mp3 = _encode_mp3(wav)
    if mp3 is not None:
        return mp3, "mp3"
    return wav, "wav"


# ---------------------------------------------------------------------------
# Cloudflare R2 storage
# ---------------------------------------------------------------------------

def _r2_client():
    import boto3  # lazy import so local TTS testing doesn't require boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def upload_to_r2(data: bytes, key: str, content_type: str) -> str:
    """Upload audio bytes to R2 and return the public CDN URL."""
    client = _r2_client()
    client.put_object(Bucket=settings.r2_bucket, Key=key, Body=data, ContentType=content_type)
    base = settings.r2_public_base_url.rstrip("/")
    return f"{base}/{key}"


# ---------------------------------------------------------------------------
# Main entry point (called by the orchestrator)
# ---------------------------------------------------------------------------

def generate_audio(text: str, lang: str, temple_slug: str) -> str:
    """text -> audio -> R2 -> public URL. Returns the CDN URL of the stored file."""
    data, ext = synthesize(text, lang)
    key = f"{temple_slug}_{lang}.{ext}"
    content_type = "audio/mpeg" if ext == "mp3" else "audio/wav"
    url = upload_to_r2(data, key, content_type)
    logger.info("Uploaded %s (%d bytes) -> %s", key, len(data), url)
    return url


# ---------------------------------------------------------------------------
# Local test:  python -m app.tasks.audio "मराठी मजकूर येथे" mr
# Saves the audio locally (no R2 needed) so you can listen using the free credit.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sample = sys.argv[1] if len(sys.argv) > 1 else "नमस्कार, हे एक चाचणी आहे."
    lang = sys.argv[2] if len(sys.argv) > 2 else "mr"

    audio_bytes, ext = synthesize(sample, lang)
    filename = f"test_{lang}.{ext}"
    with open(filename, "wb") as fh:
        fh.write(audio_bytes)
    print(f"Saved {filename} ({len(audio_bytes)} bytes)")
