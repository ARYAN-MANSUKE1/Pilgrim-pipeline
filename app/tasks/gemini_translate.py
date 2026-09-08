"""
Gemini translation engine (audio stays on Sarvam).

Exposes `translate(text, source_lang, target_lang) -> str`, matching the
TranslateFn signature that `structured_translate.translate_html` expects. It only
ever receives PLAIN TEXT (translate_html never sends HTML tags), so this module
just does high-quality, devotional-tone translation and returns the text.

Uses the Gemini REST API via httpx (no extra SDK) for consistency with the
Sarvam client. Model + key come from app.config.settings.
"""

from __future__ import annotations

import logging
import threading

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import LANGUAGE_NAMES, settings
from app.tasks import costs

logger = logging.getLogger(__name__)

# Devotional-tone, structure-safe translation. The placeholder note keeps the
# bin-packing sentinel (structured_translate) intact so batched calls stay cheap.
_SYSTEM = (
    "You are an expert translator for a Hindu temple and pilgrimage website. "
    "Translate the user's text into {target} using natural, fluent, respectful "
    "devotional language. Keep deity names, saints' names, Sanskrit and religious "
    "terms, temple and place names, dates and numbers accurate and recognisable. "
    # Digits: Gemini localised them for Gujarati/Marathi but left ASCII for
    # Telugu, Malayalam, Tamil and Punjabi -- inconsistent across the site. Native
    # numerals are also SAFER for the audio: the number-to-words step converts a
    # language's own digits correctly, but mis-reads digits from another script
    # (Devanagari 130 fed to Kannada came back as "one three zero").
    "Write all digits in {target}'s own numeral script, never Western/ASCII "
    "digits, and never in another language's numerals. Phone numbers included. "
    # Never put a literal example token in this prompt: the model copied the old
    # sample string ("zZqSEGqZz") straight into 127 published translations, once
    # in place of a distance in km. Describe the rule, do not demonstrate it.
    "Preserve any placeholder tokens and symbols exactly as given, in the same "
    "positions, but never invent one and never copy an example from these "
    "instructions into your answer. "
    # Latin-script leaks: 12% of temples came back with an English word left in
    # the middle of Indic text ("chandelier", "labyrinth", "worm"), which a
    # reader notices immediately.
    "Write every word in {target}'s own script. Do not leave English words in "
    "the output; translate them. The only Latin text allowed is inside URLs, "
    "email addresses and established acronyms (GSRTC, BAPS). "
    "Return ONLY the translation — no quotes, notes, or explanations."
)

# Gemini 3.x renamed thinkingBudget -> thinkingLevel. Set once if the model
# rejects our first guess, so we send the other spelling instead of none.
_THINKING_SWAPPED = False


def _thinking_cfg() -> dict:
    """The knob that keeps thinking off -- worth getting right.

    2.5 models take thinkingBudget 0 (thinking fully off). Gemini 3.x renamed it
    to thinkingLevel and cannot disable thinking at all; "minimal" is the floor.
    Sending the wrong spelling is a bare 400, and the previous code answered that
    400 by DELETING the field -- which does not mean "no thinking", it means "use
    the model's default budget". That silently billed 2,413 thinking tokens per
    call at the output rate: half of one real invoice. So never drop it, swap it.
    """
    three = "gemini-3" in settings.gemini_model
    if _THINKING_SWAPPED:
        three = not three
    return {"thinkingLevel": "minimal"} if three else {"thinkingBudget": 0}


class EmptyTranslation(RuntimeError):
    """Gemini answered 200 but with no usable text. Usually transient."""


_SAFETY = [
    {"category": c, "threshold": "BLOCK_NONE"}
    for c in (
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "HARM_CATEGORY_DANGEROUS_CONTENT",
    )
]


def _name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, code)


# Lazily-loaded ADC credentials (used only when settings.gemini_use_adc is True).
# Guarded by a lock so parallel language translations don't race on the refresh.
_adc_creds = None
_adc_lock = threading.Lock()


def _auth_headers() -> dict:
    """Auth headers for the Gemini call: ADC Bearer token (dev) or API key (prod)."""
    if settings.gemini_use_adc:
        global _adc_creds
        import google.auth
        import google.auth.transport.requests
        with _adc_lock:
            if _adc_creds is None:
                _adc_creds, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            if not _adc_creds.valid:
                _adc_creds.refresh(google.auth.transport.requests.Request())
            token = _adc_creds.token
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not set (and gemini_use_adc is False)")
    return {"x-goog-api-key": settings.gemini_api_key, "Content-Type": "application/json"}


def _endpoint_url() -> str:
    """Vertex AI endpoint for the ADC path (accepts cloud-platform scope); the
    AI Studio generativelanguage endpoint for the API-key path (production)."""
    if settings.gemini_use_adc:
        loc = settings.vertex_location
        host = "aiplatform.googleapis.com" if loc == "global" else f"{loc}-aiplatform.googleapis.com"
        return (
            f"https://{host}/v1/projects/{settings.gcp_project}"
            f"/locations/{loc}/publishers/google/models/{settings.gemini_model}:generateContent"
        )
    return f"{settings.gemini_base_url}/models/{settings.gemini_model}:generateContent"


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    # EmptyTranslation included: Gemini intermittently returns a candidate with
    # no text, and that used to lose a language permanently -- the retry only
    # covered HTTP errors, and an empty body is a 200.
    retry=retry_if_exception_type((httpx.HTTPError, EmptyTranslation)),
    reraise=True,
)
def translate(text: str, source_lang: str, target_lang: str) -> str:
    """Translate plain text source_lang -> target_lang via Gemini. Retries on HTTP errors."""
    global _THINKING_SWAPPED
    if not text or not text.strip():
        return text

    source, target = _name(source_lang), _name(target_lang)
    url = _endpoint_url()
    payload = {
        "systemInstruction": {"parts": [{"text": _SYSTEM.format(target=target)}]},
        "contents": [{"role": "user", "parts": [{"text": f"Translate this from {source} to {target}:\n\n{text}"}]}],
        # Keep thinking at its floor: it adds no accuracy on a translation (only
        # embellishment over the literal source) and thought tokens bill at the
        # OUTPUT rate. Measured on 3.5-flash-lite: 2,413 thought tokens per call,
        # 1.08x the visible output -- i.e. half the invoice, for nothing.
        "generationConfig": {"temperature": 0.3, "topP": 0.95, "maxOutputTokens": 16384,
                             "thinkingConfig": _thinking_cfg()},
        "safetySettings": _SAFETY,
    }

    resp = httpx.post(url, json=payload, headers=_auth_headers(), timeout=120)
    # A 400 here usually means we guessed the wrong spelling for this model, so
    # retry with the OTHER one -- never by removing it (see _thinking_cfg).
    if resp.status_code == 400 and not _THINKING_SWAPPED:
        _THINKING_SWAPPED = True
        payload["generationConfig"]["thinkingConfig"] = _thinking_cfg()
        logger.info("%s rejected thinkingConfig; retrying as %s",
                    settings.gemini_model, payload["generationConfig"]["thinkingConfig"])
        resp = httpx.post(url, json=payload, headers=_auth_headers(), timeout=120)
    resp.raise_for_status()
    data = resp.json()

    costs.record_translation(data.get("usageMetadata"), target_lang)

    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason")
        raise EmptyTranslation(f"Gemini returned no candidates (blockReason={reason})")

    cand = candidates[0]
    parts = (cand.get("content") or {}).get("parts") or []
    out = "".join(p.get("text", "") for p in parts).strip()

    if cand.get("finishReason") == "MAX_TOKENS":
        logger.warning("Gemini hit MAX_TOKENS; translation may be truncated (len=%d).", len(out))
    if not out:
        # Say WHY. "empty text" alone told us nothing when Malayalam dropped out
        # of a temple mid-run; finishReason distinguishes a transient blip from a
        # SAFETY/RECITATION block that will never succeed.
        raise EmptyTranslation(
            f"Gemini returned empty text (finishReason={cand.get('finishReason')}, "
            f"safety={cand.get('safetyRatings')})"
        )
    return out


_DETECT_CODES = ("mr", "en", "hi", "gj", "ta", "te", "ml", "kn")
_DETECT_NAMES = {"marathi": "mr", "english": "en", "hindi": "hi", "gujarati": "gj",
                 "tamil": "ta", "telugu": "te", "malayalam": "ml", "kannada": "kn"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15),
       retry=retry_if_exception_type((httpx.HTTPError,)), reraise=True)
def detect_language(text: str):
    """Identify which of our 8 languages `text` is in. Returns a code (e.g. 'ta') or None.
    Only call this when the source language is genuinely unknown ('Other') — for known
    languages, pass the code straight through and skip this call."""
    import re as _re
    sample = _re.sub(r"<[^>]+>", " ", text or "")[:1500].strip()
    if not sample:
        return None
    prompt = ("Identify the language of the text below. Reply with EXACTLY ONE code and nothing else:\n"
              "mr=Marathi, en=English, hi=Hindi, gj=Gujarati, ta=Tamil, te=Telugu, ml=Malayalam, kn=Kannada.\n\n"
              "Text:\n" + sample)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        # No thinking needed for classification -> faster, cheaper, avoids empty output.
        # Same spelling rule as translate(): a hardcoded thinkingBudget 400s on 3.x.
        "generationConfig": {"temperature": 0, "maxOutputTokens": 64,
                             "thinkingConfig": _thinking_cfg()},
        "safetySettings": _SAFETY,
    }
    resp = httpx.post(_endpoint_url(), json=payload, headers=_auth_headers(), timeout=60)
    resp.raise_for_status()
    cand = (resp.json().get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    out = "".join(p.get("text", "") for p in parts).strip().lower()
    for w in _re.findall(r"[a-z]+", out):
        if w in _DETECT_CODES:
            return w
        if w in _DETECT_NAMES:
            return _DETECT_NAMES[w]
    return None
