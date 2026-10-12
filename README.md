# Pilgrim Pipeline

One language in, all languages out. Give a temple's description in a single Indian
language and the pipeline fills in every other language, generates a voice recording
for each, and writes it all back into WordPress. Built for the Pilgrim Data temple
platform (~2,360 temples on pilgrimdata.in).

## Features

- **Structure-preserving translation** (Google Gemini; model set by `GEMINI_MODEL`,
  production uses `gemini-3.1-flash-lite`) - images and paragraphs survive intact.
- **Checked before it is saved** - every translation is validated (right script,
  not the source handed back, not cut short, no runaway repetition, no leaked
  markers) and retried sentence by sentence; anything still wrong is never saved.
- **Text-to-speech** in every language (Sarvam Bulbul v3; v2 was retired by Sarvam).
- **WordPress write-back** - content, titles, audio and photos into the `temple`
  post type via the REST API.
- **Admin dashboard** (FastAPI, login-protected) with a background job queue that
  survives restarts, pauses itself when a provider runs out of credit, and shows
  what is left to do, what it will cost and what was spent today.
- **Ad campaigns** - create, edit, pause and track the site's temple-page ads.

**Languages:** Marathi, English, Hindi, Gujarati, Tamil, Telugu, Malayalam, Kannada,
Bengali, Punjabi (`mr en hi gj ta te ml kn bn pa`).

## Repository layout

```
app/
  config.py                    Env-driven settings: API keys, model names, language maps
  tasks/
    structured_translate.py    HTML-safe splitter (structure survives) + span-strip cost fix
    gemini_translate.py        Gemini translate() + detect_language() (Vertex ADC or API key)
    source_detect.py           Pick the source language by visible-text length
    tts_normalize.py           Expand abbreviations for correct speech
    audio.py                   Chunk -> Sarvam TTS -> stitch WAV -> optional MP3 -> R2
    wp_client.py               WordPress REST fetch / write-back / media upload (with retries)

run_temple.py                  CLI: run the full pipeline for one temple by ID

dashboard/
  main.py                      Routes + WordPress connection
  pipeline.py                  Per-temple processing (translate / audio / both)
  jobs.py                      Background job queue with crash-resume
  sheet_sync.py                Push progress to the team's Google Sheet
  static/                      home / process / add / ads / languages pages (plain HTML + JS)

app/tasks/safe_translate.py    Validate-then-save translation (see "Checked before it is saved")
app/tasks/field_checks.py      Is a field really in the language it claims to be?
translate_live.py              One-off runner for the live-only temples
new theme/                     Master copies of the live WordPress theme files

test_*.py, test_ads.php        Checks (see "Run the checks")
.env.example                   Copy to .env and fill in
```

Not committed (shared out of band): audio samples, cost PDFs, WordPress theme files.
See `.gitignore`.

## Setup

1. Requires **Python 3.11+** (tested on 3.13 / 3.14).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create your config from the template:
   ```bash
   cp .env.example .env
   ```
4. Fill in `.env` using the table below.

### Environment variables

| Key | Purpose |
| --- | --- |
| `SARVAM_API_KEY` | Sarvam key for audio (TTS) |
| `WP_URL`, `WP_USER`, `WP_APP_PASSWORD` | WordPress site + Application Password (write-back) |
| `GEMINI_API_KEY` | Gemini via AI Studio - the simplest option, **or** |
| `GEMINI_USE_ADC=1` + `GCP_PROJECT` | Gemini via Vertex AI with Application Default Credentials |
| `DASHBOARD_USER`, `DASHBOARD_PASSWORD` | Dashboard login. **Required** if the dashboard is reachable from other computers; with no password it only answers on the server itself |
| `LIVE_WP_URL`, `LIVE_WP_USER`, `LIVE_WP_APP_PASSWORD` | The live site, for the "live" columns in the CSV export and sheet |
| `GOOGLE_SA_JSON`, `SHEET_ID` | Optional: service-account key file + sheet id for the Google Sheet sync |
| `TTS_SPEAKER` | Sarvam v3 voice (default `priya`; samples in `voice_samples/`) |
| `AUDIO_ENABLED` | `0` (default): audio generation is switched off everywhere - buttons, queued jobs and API. Set `1` to turn it back on |

Notes:

- The Pilgrim org policy blocks plain Gemini API keys, so **production uses ADC**:
  run `gcloud auth application-default login`, set `GEMINI_USE_ADC=1` and
  `GCP_PROJECT`, and optionally `VERTEX_LOCATION=global`.
- **ffmpeg is optional.** If installed, audio is compressed to MP3; otherwise it
  stays WAV.

## Usage

### Run one temple from the command line

```bash
python run_temple.py <temple_id>            # auto-detect source (mr > en > hi)
python run_temple.py <temple_id> en         # force English as the source
python run_temple.py <temple_id> en mr,hi   # force source + only these target languages
```

The runner pulls the temple from WordPress, detects (or uses) the source language,
translates into the other languages, generates audio, and writes everything back.
Open the temple on the staging site to see the result.

### Run the admin dashboard

On Windows, double-click **`Start Dashboard.bat`**. Or from a terminal:

```bash
uvicorn dashboard.main:app --port 8000
```

Open http://localhost:8000 (on a server: set `DASHBOARD_PASSWORD` first and serve it
over HTTPS). Pages:

- **Home** - what is left to translate / voice per language, estimated cost,
  spent today, one-click "Translate all" / "Generate audio for all", recent jobs.
- **Process Temples** - search, select temples, choose translate and/or audio per
  language, and run; Export CSV (with the live site's languages and links).
- **Add Temple** - paste source content, add photos (first = cover), choose languages,
  and create the temple in WordPress as a **Draft** (you publish it there yourself).
- **Ads** - ad campaigns: image, link, placement (top / left / right / bottom),
  dates, target states and districts, pause / edit / delete, impressions and clicks.
  Needs the theme's `functions.php` from `new theme/`.
- **Languages** - only works with a theme that has the language registry
  (`pilgrim/v1/languages`); the current theme has its 10 languages built in.

If Gemini or Sarvam runs out of credit, a red banner names the provider, the queue
pauses with nothing lost, and **Resume** continues after a top-up. The queue also
pauses when five temples in a row fail for a system reason (wrong API key, provider or
website down), instead of marking every remaining temple failed.

The website the dashboard reads and writes is shown next to its name on every page.
Jobs and counts saved for one website are never resumed or shown for another, so
changing `WP_URL` (for example staging -> live) is safe.

### Run the checks

```bash
python test_source_detect.py        # source-language choice
python test_structured_translate.py # HTML structure survives translation
python test_safe_translate.py       # validation + retry, full pipeline flow
python test_edge_cases.py           # 13 failure modes through the real pipeline
python test_credit_pause.py         # queue pauses on out-of-credit, resumes
python test_queue_guards.py         # wrong-site jobs not resumed, audio switch, failure-streak pause
python -m app.tasks.field_checks
python -m app.tasks.costs
python -m dashboard.sheet_sync
php test_ads.php                    # ad matching in the theme
```

None of these call a paid API or write to WordPress.

## How it works

1. **No HTML tags reach the translator.** `translate_html` splits the body on blank
   lines and tags, translates only the text segments, and reassembles - so images
   and paragraph breaks are preserved.
2. **Cost control.** `strip_cosmetic_spans` removes per-word `<span>` wrappers before
   translating, collapsing hundreds of tiny API calls into one call per language.
3. **Correct pronunciation.** `tts_normalize` expands Marathi/Hindi abbreviations
   (for example "ta." -> "taluka", "ji." -> "jilha") before speech.
4. **Long text.** Sarvam caps each request at 2,500 characters, so audio is chunked
   on sentence boundaries and stitched back into one file using the stdlib `wave`
   module.
5. **Resilience.** WordPress writes and TTS calls retry on transport errors, and the
   dashboard's job queue is persisted to disk so it resumes after a crash or restart.
