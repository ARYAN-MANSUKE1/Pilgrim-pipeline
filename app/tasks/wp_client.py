"""
WordPress write-back client.

Three operations:
  1. fetch_temple_text — GET ACF content field for a temple, returns plain text (HTML stripped)
  2. upload_audio      — POST audio bytes to /wp/v2/media, returns attachment ID
  3. set_audio_field   — PATCH ACF audio file field on a temple post with the attachment ID
"""

import html
import json
import logging
import re
import time
from typing import Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import LANGUAGE_CODES, settings

# 10Web's server/firewall occasionally drops a request mid-flight (WinError 10054 /
# connection reset), especially on large or rapid POSTs. Retry the WP calls with
# backoff so a single transient drop doesn't fail a whole temple. Only network-level
# errors are retried (not 4xx), so a genuine bad request still surfaces immediately.
_wp_retry = retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    retry=retry_if_exception_type(httpx.TransportError),
    reraise=True,
)

SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
_TRANSLATE_MAX_CHARS = 1800

_IMG_RE = re.compile(r'<img[^>]+/?>', re.IGNORECASE)
_BLOCK_TAG_RE = re.compile(r'(</(?:p|h[1-6]|li|ul|ol|blockquote)>)', re.IGNORECASE)

# ── Gemini translation (Engineer 1's approach) ────────────────────────────────
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

_GEMINI_SYSTEM = (
    "You are a specialized spiritual and religious text translator and content creator. "
    "Your task is to take temple data or religious documents and convert them into the requested target language. "
    "The tone must be deeply respectful, emotionally resonant, and spiritually accurate. "
    "Use appropriate honorifics and vocabulary that reflects the sanctity of the subject matter. "
    "Ensure the translation uses high-quality, culturally rich, and sacred/pure vocabulary suitable for "
    "religious and spiritual contexts, maintaining a dignified, sacred tone throughout. "
    "Preserve all factual details exactly: place names, dates, distances, phone numbers, timings. "
    "Keep Sanskrit/ritual terms recognisable (e.g. Garbhagriha, Prana Pratishtha, Abhishek, Aarti, Prasad, "
    "Pradakshina, Kalash, Warkari, Dindi, Akhand Saptah) rather than over-translating them. "
    "Return ONLY a JSON object with exactly two keys: \"title\" and \"content\". No markdown fences, no preamble."
)

TITLE_FIELD_KEYS = {
    "mr": "marathi_title",
    "en": "english_title",
    "hi": "hindi_title",
    "gj": "gujarati_title",
    "ta": "tamil_title",
    "te": "telugu_title",
    "ml": "malayalam_title",
    "kn": "kannada_title",
}

LANG_NAMES = {
    "mr": "Marathi",
    "en": "English",
    "hi": "Hindi",
    "gj": "Gujarati",
    "ta": "Tamil",
    "te": "Telugu",
}


def strip_html(raw: str) -> str:
    """Remove HTML tags and decode entities, leaving plain text for TTS."""
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

logger = logging.getLogger(__name__)

# ACF field key for each language's audio upload field.
AUDIO_FIELD_KEYS = {
    "mr": "marathi_audio",
    "en": "english_audio",
    "hi": "hindi_audio",
    "gj": "gujarati_audio",  # site uses 'gj' switcher code, field key is gujarati_audio
    "ta": "tamil_audio",     # field not yet created — Engineer 1 will add
    "te": "telugu_audio",    # field not yet created — Engineer 1 will add
    "ml": "malayalam_audio", # new — ACF field must be created in WP
    "kn": "kannada_audio",   # new — ACF field must be created in WP
}


CONTENT_FIELD_KEYS = {
    "mr": "mr_translation",
    "en": "en_translation",
    "hi": "hi_translation",
    "gj": "gujarati_content",   # site uses 'gj' code; ACF field is gujarati_content
    "ta": "tamil_content",      # confirmed from Engineer 1's agent.py
    "te": "telugu_content",     # confirmed from Engineer 1's agent.py
    "ml": "malayalam_content",  # new — ACF field must be created in WP
    "kn": "kannada_content",    # new — ACF field must be created in WP
}


def _auth() -> tuple[str, str]:
    return (settings.wp_user, settings.wp_app_password)


def _base() -> str:
    return settings.wp_url.rstrip("/") + "/wp-json/wp/v2"


@_wp_retry
def fetch_all_content(post_id: int) -> dict[str, str]:
    """Return {lang_code: raw_html} for every language on a temple. Empty string if field is blank."""
    url = f"{_base()}/temple/{post_id}"
    resp = httpx.get(url, params={"context": "edit"}, auth=_auth(), timeout=30)
    resp.raise_for_status()
    acf = resp.json().get("acf", {})
    return {
        lang: (acf.get(field) or "")
        for lang, field in CONTENT_FIELD_KEYS.items()
    }


def _translate_chunk(text: str, src: str, tgt: str) -> str:
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "input": text,
        "source_language_code": LANGUAGE_CODES[src],
        "target_language_code": LANGUAGE_CODES[tgt],
        "model": "sarvam-translate:v1",
        "enable_preprocessing": False,
    }
    resp = httpx.post(SARVAM_TRANSLATE_URL, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()["translated_text"]


def translate_text(html: str, src: str, tgt: str) -> str:
    """
    Translate HTML content from src → tgt.
    Images are extracted and restored; all other HTML is stripped before
    sending to Sarvam (the API rejects HTML tags with a 400).
    """
    from app.tasks.audio import chunk_text

    # Pull images out before stripping so they survive translation unchanged
    placeholders: dict[str, str] = {}
    counter = 0

    def sub_img(m: re.Match) -> str:
        nonlocal counter
        key = f"[[IMG{counter}]]"
        placeholders[key] = m.group(0)
        counter += 1
        return f" {key} "

    no_imgs = _IMG_RE.sub(sub_img, html)

    # Strip remaining HTML tags → plain text for Sarvam
    plain = strip_html(no_imgs)

    # Translate in plain-text chunks
    chunks = chunk_text(plain, max_chars=_TRANSLATE_MAX_CHARS)
    translated = " ".join(_translate_chunk(c, src, tgt) for c in chunks)

    # Restore image tags
    for key, tag in placeholders.items():
        translated = translated.replace(key, f"\n{tag}\n")

    return translated


@_wp_retry
def write_translation(post_id: int, lang: str, text: str) -> None:
    """Write translated text into the ACF content field for a temple."""
    field_key = CONTENT_FIELD_KEYS.get(lang)
    if not field_key:
        raise ValueError(f"No content field for lang={lang!r}")
    url = f"{_base()}/temple/{post_id}"
    resp = httpx.post(url, json={"acf": {field_key: text}}, auth=_auth(), timeout=30)
    resp.raise_for_status()
    logger.info("Wrote %s translation (%d chars) → post %d", lang, len(text), post_id)


def _collapse_wp_spans(html: str) -> str:
    """Remove <span style="font-weight: 400;"> wrappers WordPress inserts around every word.
    They're visually identical to unstyled text and cause per-word translation calls."""
    return re.sub(
        r'<span\s+style=["\']font-weight:\s*400;?["\']>(.*?)</span>',
        r'\1',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


def translate_with_sarvam(source_title: str, source_content_html: str, target_lang: str, source_lang: str = "mr") -> dict:
    """
    Translate title + content to target_lang using Sarvam Translate.
    HTML structure is preserved — only visible text nodes between tags are translated.
    """
    from app.tasks.audio import chunk_text

    def _translate_text(text: str) -> str:
        if not text.strip():
            return text
        chunks = chunk_text(text.strip(), max_chars=_TRANSLATE_MAX_CHARS)
        return " ".join(_translate_chunk(c, source_lang, target_lang) for c in chunks)

    def translate_html_nodes(html: str) -> str:
        html = _collapse_wp_spans(html)
        parts = re.split(r'(<[^>]+>)', html)
        return "".join(
            _translate_text(p) if not p.startswith("<") and p.strip() else p
            for p in parts
        )

    return {
        "title":   _translate_text(strip_html(source_title)[:500]),
        "content": translate_html_nodes(source_content_html),
    }


def translate_with_gemini(source_title: str, source_content_plain: str, target_lang: str, source_lang: str = "mr") -> dict:
    """
    Translate a temple's title + content into target_lang using Gemini.
    source_lang: the language code of the source text (default "mr" for Marathi).
    Returns {"title": ..., "content": ...}.
    """
    src_name = LANG_NAMES.get(source_lang, "Marathi")
    lang_name = LANG_NAMES[target_lang]
    prompt = (
        f"Translate the following {src_name} temple description into {lang_name}.\n\n"
        f"SOURCE TITLE:\n{source_title}\n\n"
        f"SOURCE CONTENT (HTML):\n{source_content_plain}\n\n"
        f"IMPORTANT: The source content is HTML. Translate ONLY the visible text between tags. "
        f"Preserve ALL HTML tags, attributes, image src URLs, class names, and structure exactly as-is. "
        f"Do not add, remove, or change any HTML tags or attributes.\n\n"
        f'Respond with JSON: {{"title": "...", "content": "..."}}'
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": _GEMINI_SYSTEM}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "title":   {"type": "STRING"},
                    "content": {"type": "STRING"},
                },
                "required": ["title", "content"],
            },
        },
    }
    for attempt in range(1, 6):
        resp = httpx.post(_GEMINI_URL, params={"key": settings.gemini_api_key}, json=body, timeout=120)
        if resp.status_code == 429:
            wait = min(60, 5 * attempt)
            logger.warning("Gemini rate limited — waiting %ds (attempt %d/5)", wait, attempt)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        raw = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(raw)
        return {"title": result.get("title", "").strip(), "content": result.get("content", "").strip()}
    raise RuntimeError("Gemini rate limit exceeded after 5 retries")


@_wp_retry
def write_title_and_content(post_id: int, lang: str, title: str, content: str) -> None:
    """Write translated title + content ACF fields back to WordPress."""
    updates = {}
    if title:
        updates[TITLE_FIELD_KEYS[lang]] = title
    if content:
        updates[CONTENT_FIELD_KEYS[lang]] = content
    url = f"{_base()}/temple/{post_id}"
    resp = httpx.post(url, json={"acf": updates}, auth=_auth(), timeout=30)
    resp.raise_for_status()
    logger.info("Wrote %s title+content → post %d", lang, post_id)


def fetch_temple_meta(post_id: int) -> dict:
    """Return {slug, title, marathi_title} for a temple."""
    url = f"{_base()}/temple/{post_id}"
    resp = httpx.get(url, params={"context": "edit"}, auth=_auth(), timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {
        "slug":          data.get("slug", f"temple-{post_id}"),
        "title":         data.get("title", {}).get("rendered", ""),
        "marathi_title": (data.get("acf", {}).get("marathi_title") or "").strip(),
    }


def fetch_temple_text(post_id: int, lang: str) -> str:
    """Fetch a temple's ACF content field and return plain text (HTML stripped)."""
    field_key = CONTENT_FIELD_KEYS.get(lang)
    if not field_key:
        raise ValueError(f"No content field mapped for lang={lang!r}")
    url = f"{_base()}/temple/{post_id}"
    resp = httpx.get(url, params={"context": "edit"}, auth=_auth(), timeout=30)
    resp.raise_for_status()
    raw = resp.json().get("acf", {}).get(field_key, "")
    return strip_html(raw)


@_wp_retry
def upload_audio(data: bytes, filename: str, content_type: str) -> int:
    """
    Upload audio bytes to the WP Media Library.
    Returns the new attachment ID.
    """
    url = f"{_base()}/media"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": content_type,
    }
    resp = httpx.post(url, content=data, headers=headers, auth=_auth(), timeout=120)
    resp.raise_for_status()
    attachment_id: int = resp.json()["id"]
    logger.info("Uploaded %s → attachment ID %d", filename, attachment_id)
    return attachment_id


@_wp_retry
def set_audio_field(post_id: int, lang: str, attachment_id: int) -> None:
    """
    Set the ACF audio file field on a temple post to the given attachment ID.
    ACF file fields accept the attachment ID (integer) via REST meta.
    """
    field_key = AUDIO_FIELD_KEYS.get(lang)
    if not field_key:
        raise ValueError(f"No ACF audio field mapped for lang={lang!r}")

    url = f"{_base()}/temple/{post_id}"
    payload = {"acf": {field_key: attachment_id}}
    resp = httpx.post(url, json=payload, auth=_auth(), timeout=30)
    resp.raise_for_status()
    logger.info("Set %s = %d on post %d", field_key, attachment_id, post_id)


def generate_and_save(
    text: str,
    lang: str,
    temple_id: int,
    temple_slug: str,
) -> Optional[int]:
    """
    Full pipeline: text → audio → WP Media → ACF field.
    Returns attachment ID on success, None if WP creds not configured (skips upload).
    """
    from app.tasks.audio import synthesize  # avoid circular at module load

    data, ext = synthesize(text, lang)
    content_type = "audio/mpeg" if ext == "mp3" else "audio/wav"
    filename = f"{temple_slug}_{lang}.{ext}"

    if not (settings.wp_url and settings.wp_user and settings.wp_app_password):
        logger.warning("WP creds not set — audio generated (%d bytes) but NOT uploaded.", len(data))
        return None

    attachment_id = upload_audio(data, filename, content_type)
    set_audio_field(temple_id, lang, attachment_id)
    return attachment_id
