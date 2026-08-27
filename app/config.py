"""Pipeline configuration. Reads from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Sarvam TTS (Bulbul v2) ---
    sarvam_api_key: str = ""
    sarvam_tts_url: str = "https://api.sarvam.ai/text-to-speech"
    sarvam_model: str = "bulbul:v2"
    # 2500 is Sarvam's ACTUAL per-request cap (verified against the API: 4000
    # returns "text: String should have at most 2500 characters"). It was set to
    # 1500, which wasted 40% of every request -- a 55k-char temple took 37 round
    # trips instead of 22. Billing is per character either way, so this is free.
    tts_max_chars: int = 2500
    tts_speaker: str = "arya"           # v2 female: anushka, manisha, vidya, arya | male: abhilash, karun, hitesh
    tts_pitch: float = 0.0             # -0.75 .. 0.75
    tts_pace: float = 1.0              # 0.3 .. 3.0
    tts_loudness: float = 1.0          # 0.3 .. 3.0
    tts_sample_rate: int = 22050       # 8000 | 16000 | 22050 | 24000
    tts_enable_preprocessing: bool = True  # normalizes numbers/English; turn off if numbers read in English

    # --- WordPress write-back (Application Password auth) ---
    wp_url: str = ""                   # e.g. https://allowing-lion-dev.10web.cloud
    wp_user: str = ""                  # WP username
    wp_app_password: str = ""          # WP Application Password (no spaces)

    # --- Gemini Translation (translation engine; audio stays Sarvam) ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"   # fast + cheap; override to gemini-2.5-flash etc.
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    # ADC mode (sample/dev only, used when org policy blocks API keys). When True,
    # auth uses Application Default Credentials (Bearer token) + gcp_project for quota,
    # instead of gemini_api_key. Production will flip this off and set gemini_api_key.
    gemini_use_adc: bool = False
    gcp_project: str = ""                     # quota/billing project for ADC calls
    vertex_location: str = "us-central1"      # Vertex region (ADC path uses Vertex AI)

    # --- Live site (migration target; staging stays in WP_URL above) ---
    live_wp_url: str = ""
    live_wp_user: str = ""
    live_wp_app_password: str = ""

    # --- Job worker ---
    # 1, not 2: the 10web staging host -- not Sarvam or Gemini -- is the
    # throughput ceiling. Two concurrent temples pushed a WP GET from 0.3s to
    # 55s and timed out every write. Costs are ContextVar-isolated
    # (app/tasks/costs.py), so raising this is safe the day WP can take it.
    job_workers: int = 1
    audio_workers: int = 3   # languages voiced concurrently within one temple

    # --- Google Sheet progress tracker (shared with the client) ---
    google_sa_json: str = ""   # path to a service-account JSON key; sheet shared with its email
    sheet_id: str = ""         # the spreadsheet id from its URL
    sheet_limit: int = 30      # rows to keep in the sheet; 0 = every temple

    # --- Cost accounting (INR) ---
    # Sarvam rate is from full-site-cost.pdf (bills per character spoken);
    # Gemini rates are Google's list price for gemini-2.5-flash -- .env sets
    # GEMINI_MODEL=gemini-2.5-flash, overriding the 2.0 default above, so these
    # must track 2.5. If you ever switch the model back, change these too.
    sarvam_inr_per_10k_chars: float = 15.0   # Bulbul v2; v3 bills 2x (applied automatically)
    gemini_usd_per_1m_input: float = 0.30    # gemini-2.5-flash list price
    gemini_usd_per_1m_output: float = 2.50
    usd_inr: float = 88.0

    # --- Cloudflare R2 (S3-compatible, future) ---
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_base_url: str = ""       # e.g. https://cdn.pilgrim.com  (or the *.r2.dev URL)


settings = Settings()

# Sarvam Bulbul TTS's COMPLETE supported-language set (both v2 and v3) -- verified
# directly against Sarvam's own API reference on 2026-08-05:
# https://docs.sarvam.ai/api-reference/text-to-speech/convert.md
# ("Sarvam_Model_API_TextToSpeechLanguage" enum). This is Sarvam's product
# surface, not ours -- it's fixed by them and changes rarely (a new model
# generation, not a routine update). If a language is missing here, that means
# Sarvam genuinely doesn't support TTS for it (confirmed absent: Assamese, Urdu,
# Sanskrit, Nepali, Konkani, Maithili) -- re-check the URL above before adding
# a code rather than guessing one; a wrong guess fails silently at audio time
# (see the Bengali/Punjabi "Unsupported language" incident this was built to
# prevent from recurring).
#
# NOTE: Gujarati is "gj" internally (matches the theme's switcher code) AND
# "gu" is accepted as an alias, since sample data / ACF sometimes uses "gu".
# "od" (Odia) is included even though the site doesn't offer it yet -- Sarvam
# supports it, so it's ready the moment it's added via the language registry.
SARVAM_SUPPORTED_LANGUAGES = {
    "hi": ("hi-IN", "Hindi"),
    "bn": ("bn-IN", "Bengali"),
    "en": ("en-IN", "English"),
    "gj": ("gu-IN", "Gujarati"),
    "gu": ("gu-IN", "Gujarati"),
    "kn": ("kn-IN", "Kannada"),
    "ml": ("ml-IN", "Malayalam"),
    "mr": ("mr-IN", "Marathi"),
    "od": ("od-IN", "Odia"),
    "pa": ("pa-IN", "Punjabi"),
    "ta": ("ta-IN", "Tamil"),
    "te": ("te-IN", "Telugu"),
}

# Internal language code -> Sarvam target_language_code (derived from the table above).
LANGUAGE_CODES = {code: pair[0] for code, pair in SARVAM_SUPPORTED_LANGUAGES.items()}

# Internal language code -> human-readable name (for the Gemini prompt; derived too).
LANGUAGE_NAMES = {code: pair[1] for code, pair in SARVAM_SUPPORTED_LANGUAGES.items()}
