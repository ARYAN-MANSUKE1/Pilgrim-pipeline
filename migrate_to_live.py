"""
Move finished work from staging to the live site -- WITHOUT regenerating anything.

Text fields copy straight across. Audio cannot: ACF stores a WordPress
attachment ID, which is meaningless on another install, so each file is
downloaded from staging, re-uploaded to live, and the NEW id written to the ACF
field. No Sarvam or Gemini call is made, so the migration costs nothing.

Temples are matched by SLUG, not post id -- the two installs number their posts
independently.

Every translated field embeds absolute staging URLs (measured: ~29 per temple,
in 100% of fields) because the source HTML did. Those are rewritten to the live
host on the way over, otherwise live would hotlink its images from staging and
break the day staging is reset. A full 10Web "Push to Live" does this search-
replace for you -- this script exists for when a full push is not an option
because live has its own newer content to preserve.

Usage:
    python migrate_to_live.py                 # dry run: says what it would do
    python migrate_to_live.py --go            # actually migrate
    python migrate_to_live.py --go --min-audio 10   # only fully-voiced temples
    python migrate_to_live.py --go --only 5   # first 5 temples (test the path)
    python migrate_to_live.py --go --force    # overwrite live fields that already have data

Needs in .env:
    LIVE_WP_URL=  LIVE_WP_USER=  LIVE_WP_APP_PASSWORD=

Safe to re-run: a language already present on live is skipped, so an
interrupted run resumes where it stopped.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.tasks import wp_client as wp
from app.tasks.source_detect import visible_text_length

DRY = "--go" not in sys.argv
FORCE = "--force" in sys.argv
ONLY = int(sys.argv[sys.argv.index("--only") + 1]) if "--only" in sys.argv else None
# --min-audio N : only temples that already have N languages voiced on staging.
# Used to migrate the fully-finished temples (all 10) ahead of the partial ones.
MIN_AUDIO = int(sys.argv[sys.argv.index("--min-audio") + 1]) if "--min-audio" in sys.argv else 0
INVENTORY = Path("migrate_inventory.json")
MIN_CHARS = 200   # same threshold the pipeline uses for "is this language translated"

# Sarvam returns 22050 Hz mono PCM. Re-encoding that to 64 kbps mono MP3 is
# transparent for speech (it is the standard podcast bitrate for exactly this
# material) and 5.5x smaller: 13.8MB -> 2.5MB per file. At full site scale the
# difference is 295 GB of WAV versus 53 GB of MP3, so this is not a preference.
# Falls back to uploading the original WAV if ffmpeg is unavailable.
MP3_BITRATE = "64k"
FFMPEG = shutil.which("ffmpeg") or str(
    Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-9.0.1-full_build/bin/ffmpeg.exe")

STAGE = settings.wp_url.rstrip("/") + "/wp-json/wp/v2"
STAGE_AUTH = (settings.wp_user, settings.wp_app_password)
LIVE = settings.live_wp_url.rstrip("/") + "/wp-json/wp/v2"
LIVE_AUTH = (settings.live_wp_user, settings.live_wp_app_password)


STAGE_HOST = settings.wp_url.split("//")[-1].strip("/")
LIVE_HOST = settings.live_wp_url.split("//")[-1].strip("/")


def relink(html: str) -> str:
    """staging.example/wp-content/... -> live.example/wp-content/... (host only)."""
    return html.replace(STAGE_HOST, LIVE_HOST) if STAGE_HOST and LIVE_HOST else html


# Both hosts drop connections under load -- staging did it during processing,
# live does it on a 19MB media POST. Every call that touches either site retries,
# because a single dropped packet must not abandon a part-migrated temple.
_net = retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=3, max=60),
             retry=retry_if_exception_type((httpx.HTTPError, httpx.RemoteProtocolError)),
             reraise=True)


@_net
def _get(url, auth, **kw):
    r = httpx.get(url, auth=auth, timeout=300, **kw)
    r.raise_for_status()
    return r


@_net
def _post(url, auth, **kw):
    r = httpx.post(url, auth=auth, timeout=600, **kw)
    r.raise_for_status()
    return r


def live_post_by_slug(slug: str) -> dict | None:
    r = _get(f"{LIVE}/temple", LIVE_AUTH, params={"slug": slug, "context": "edit"})
    hits = r.json()
    return hits[0] if hits else None


def to_mp3(wav: bytes, filename: str) -> tuple[bytes, str, str]:
    """WAV bytes -> (mp3 bytes, .mp3 filename, mime). Returns the WAV untouched
    if ffmpeg fails, so a conversion problem can never lose a recording."""
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / "in.wav", Path(d) / "out.mp3"
        src.write_bytes(wav)
        try:
            subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                            "-i", str(src), "-ac", "1", "-b:a", MP3_BITRATE, str(dst)],
                           check=True, capture_output=True, timeout=600)
            out = dst.read_bytes()
        except Exception as e:  # noqa: BLE001
            print(f"        ffmpeg failed ({e}); uploading the original WAV")
            return wav, filename, "audio/wav"
    if not out:
        return wav, filename, "audio/wav"
    return out, filename[:-4] + ".mp3", "audio/mpeg"


def copy_audio(att_id: int, live_id: int, lang: str) -> int:
    """Download one file from staging, upload it to live, return the new id."""
    media = _get(f"{STAGE}/media/{att_id}", STAGE_AUTH).json()
    src_url = media["source_url"]
    blob = _get(src_url, None).content
    filename = src_url.rsplit("/", 1)[-1]
    ctype = media.get("mime_type") or "audio/wav"

    if filename.lower().endswith(".wav") and Path(FFMPEG).exists():
        blob, filename, ctype = to_mp3(blob, filename)

    r = _post(
        f"{LIVE}/media", LIVE_AUTH, content=blob,
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "Content-Type": ctype},
    )
    return r.json()["id"]


def preflight() -> None:
    """Confirm live is reachable and actually has the ACF fields we write.

    WordPress silently DROPS acf keys that are not registered -- a migration
    would report success while writing nothing. Checked once, up front, against
    a real temple on live."""
    r = _get(f"{LIVE}/temple", LIVE_AUTH, params={"per_page": 1, "context": "edit"})
    posts = r.json()
    if not posts:
        sys.exit("live has no 'temple' posts -- is the post type the same?")
    acf = posts[0].get("acf")
    if acf is None:
        sys.exit("live returns no 'acf' key -- is ACF-to-REST enabled there?")
    wanted = set(wp.CONTENT_FIELD_KEYS.values()) | set(wp.TITLE_FIELD_KEYS.values())         | set(wp.AUDIO_FIELD_KEYS.values())
    missing = sorted(f for f in wanted if f not in acf)
    print(f"live: {settings.live_wp_url}  ({len(wanted) - len(missing)}/{len(wanted)} ACF fields present)")
    if missing:
        print("  MISSING on live -- these languages cannot be migrated until "
              "the fields are created:")
        for f in missing:
            print("   ", f)
        if not DRY:
            sys.exit("refusing to migrate into fields that do not exist -- "
                     "ask for them to be added, or re-run as a dry run to see the rest")
    print()


def main() -> None:
    if not (settings.live_wp_url and settings.live_wp_user and settings.live_wp_app_password):
        sys.exit("LIVE_WP_URL / LIVE_WP_USER / LIVE_WP_APP_PASSWORD are not set in .env")
    if not INVENTORY.exists():
        sys.exit(f"{INVENTORY} missing -- run the inventory scan first")

    wp.refresh_language_fields()
    preflight()
    items = json.loads(INVENTORY.read_text(encoding="utf-8"))
    if MIN_AUDIO:
        before = len(items)
        items = [i for i in items if len(i["audio"]) >= MIN_AUDIO]
        print(f"--min-audio {MIN_AUDIO}: {len(items)} of {before} temples selected")
    if ONLY:
        items = items[:ONLY]
    print(f"{'DRY RUN -- nothing will be written' if DRY else 'MIGRATING'}: {len(items)} temples\n")

    stats = {"matched": 0, "missing": 0, "text": 0, "audio": 0, "skipped": 0, "failed": 0}
    for n, it in enumerate(items, 1):
        try:
            live = live_post_by_slug(it["slug"])
        except Exception as e:  # noqa: BLE001
            print(f"[{n}/{len(items)}] {it['slug'][:44]}  LOOKUP FAILED: {e}")
            stats["failed"] += 1
            continue
        if not live:
            print(f"[{n}/{len(items)}] {it['slug'][:44]}  NOT ON LIVE -- skipped")
            stats["missing"] += 1
            continue
        stats["matched"] += 1
        live_acf = live.get("acf") or {}
        stage = _get(f"{STAGE}/temple/{it['id']}", STAGE_AUTH, params={"context": "edit"}).json()
        stage_acf = stage.get("acf") or {}

        # --- text: content + title
        #
        # Content: live often holds a 56-125 character stub (just a heading)
        # where staging has the real 5,000+ character article. Skipping every
        # non-empty field would leave those stubs in place forever, so a field
        # is also filled when live is BELOW the same MIN_CHARS threshold the
        # pipeline uses to decide whether a language counts as translated.
        # Live content that is genuinely long-form is never touched.
        #
        # Titles: a title is never 200 characters, so the rule there stays
        # "fill only if empty".
        # Every language, not just it["text"] -- that list excluded each temple's
        # SOURCE language on the assumption live already had it. Wrong for 5 of
        # the first 25: live's Marathi was empty or a 54-char stub while staging
        # held the full article. The MIN_CHARS rule below is what protects real
        # content, so there is no reason to pre-exclude anything.
        updates = {}
        for lang in wp.CONTENT_FIELD_KEYS:
            f = wp.CONTENT_FIELD_KEYS.get(lang)
            if f and visible_text_length(stage_acf.get(f) or "") >= MIN_CHARS:
                live_len = visible_text_length(live_acf.get(f) or "")
                if FORCE or live_len < MIN_CHARS:
                    updates[f] = relink(stage_acf[f])
            t = wp.TITLE_FIELD_KEYS.get(lang)
            if t and (stage_acf.get(t) or "").strip():
                if FORCE or not (live_acf.get(t) or "").strip():
                    updates[t] = relink(stage_acf[t])
        if updates:
            relinked = sum(v.count(LIVE_HOST) for v in updates.values() if isinstance(v, str))
            print(f"[{n}/{len(items)}] {it['slug'][:44]}  text: {len(updates)} field(s), "
                  f"{relinked} url(s) relinked")
            if not DRY:
                _post(f"{LIVE}/temple/{live['id']}", LIVE_AUTH, json={"acf": updates})
            stats["text"] += len(updates)

        # --- audio: re-upload each file, then point the ACF field at the new id
        for lang, att in zip(it["audio"], it["aids"]):
            f = wp.AUDIO_FIELD_KEYS.get(lang)
            if not f or not att:
                continue
            if live_acf.get(f) and not FORCE:
                stats["skipped"] += 1
                continue
            print(f"[{n}/{len(items)}] {it['slug'][:36]}  audio [{lang}] -> live")
            if DRY:
                stats["audio"] += 1
                continue
            try:
                new_id = copy_audio(att, live["id"], lang)
                _post(f"{LIVE}/temple/{live['id']}", LIVE_AUTH, json={"acf": {f: new_id}})
                stats["audio"] += 1
            except Exception as e:  # noqa: BLE001 -- one file must not stop the run
                print(f"        [{lang}] AUDIO COPY FAILED: {e}")
                stats["failed"] += 1

    print("\n" + json.dumps(stats, indent=2))
    if DRY:
        print("\nDry run only. Re-run with --go to apply.")


if __name__ == "__main__":
    main()
