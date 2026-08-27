"""
Push a translated UI chrome dictionary to WordPress (pilgrim/v1/ui-i18n).

This is the write side of app.tasks.ui_strings: translate_ui_strings() produces
the {key: text} dictionary for one language; push_ui_strings() saves it into the
site's pilgrim_ui_i18n option, where functions.php reads it on every page load.

Requires WP_URL / WP_USER / WP_APP_PASSWORD in .env (same credentials as the
rest of the pipeline — the endpoint requires manage_options, so use an admin
Application Password).
"""

from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

_ENDPOINT = "/wp-json/pilgrim/v1/ui-i18n"


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=retry_if_exception_type((httpx.TransportError,)),
    reraise=True,
)
def push_ui_strings(lang: str, strings: dict[str, str]) -> dict:
    """POST one language's chrome dictionary to WordPress. Returns the JSON response."""
    url = settings.wp_url.rstrip("/") + _ENDPOINT
    resp = httpx.post(
        url,
        json={"lang": lang, "strings": strings},
        auth=(settings.wp_user, settings.wp_app_password),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
