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
import subprocess
import wave
from typing import List, Tuple

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import LANGUAGE_CODES, settings
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

    sentences = [s.strip() for s in _SENTENCE_RE.findall(text) if s.strip()]
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

def _encode_mp3(wav_bytes: bytes) -> bytes | None:
    """Convert WAV -> MP3 via ffmpeg. Returns None if ffmpeg is unavailable."""
    if not shutil.which("ffmpeg"):
        return None
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-i", "pipe:0", "-f", "mp3", "-b:a", "128k", "pipe:1"],
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
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No text to synthesize")

    logger.info("Synthesizing %d chunk(s) for lang=%s", len(chunks), lang)
    wav_segments: List[bytes] = []
    for i, chunk in enumerate(chunks, 1):
        segments = _synthesize_chunk(chunk, lang_code)
        wav_segments.extend(segments)
        logger.info("  chunk %d/%d done (%d chars, %d segment(s))", i, len(chunks), len(chunk), len(segments))

    wav = _stitch_wav(wav_segments)
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
