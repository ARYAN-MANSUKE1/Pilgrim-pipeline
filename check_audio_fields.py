"""Print ACF fields for temple 12646 to confirm field keys and audio values."""
import json
import sys
import httpx
from app.config import settings

sys.stdout.reconfigure(encoding="utf-8")

resp = httpx.get(
    f"{settings.wp_url.rstrip('/')}/wp-json/wp/v2/temple/12646",
    params={"context": "edit"},
    auth=(settings.wp_user, settings.wp_app_password),
    timeout=30,
)
resp.raise_for_status()
acf = resp.json().get("acf", {})

for key, val in acf.items():
    if isinstance(val, str):
        preview = val[:80].replace("\n", " ")
    elif isinstance(val, dict):
        preview = f"[file id={val.get('ID') or val.get('id')} url={str(val.get('url',''))[:50]}]"
    else:
        preview = json.dumps(val)[:80]
    print(f"  {key:30s} = {preview}")
