"""Pipeline configuration. Reads from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Sarvam TTS (Bulbul v2) ---
    sarvam_api_key: str = ""
    sarvam_tts_url: str = "https://api.sarvam.ai/text-to-speech"
    sarvam_model: str = "bulbul:v2"
    tts_max_chars: int = 1500          # v2 per-request limit
    tts_speaker: str = "abhilash"       # v2 female: anushka, manisha, vidya, arya | male: abhilash, karun, hitesh
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

    # --- Cloudflare R2 (S3-compatible, future) ---
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = ""
    r2_public_base_url: str = ""       # e.g. https://cdn.pilgrim.com  (or the *.r2.dev URL)


settings = Settings()

# Internal language code -> Sarvam target_language_code
# NOTE: Gujarati is "gj" internally (matches the theme's switcher code) AND "gu"
# is accepted as an alias, since sample data / ACF sometimes uses "gu".
LANGUAGE_CODES = {
    "mr": "mr-IN",
    "hi": "hi-IN",
    "en": "en-IN",
    "gj": "gu-IN",
    "gu": "gu-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "ml": "ml-IN",
    "kn": "kn-IN",
}

# Internal language code -> human-readable name (for the Gemini prompt).
LANGUAGE_NAMES = {
    "mr": "Marathi",
    "hi": "Hindi",
    "en": "English",
    "gj": "Gujarati",
    "gu": "Gujarati",
    "ta": "Tamil",
    "te": "Telugu",
    "ml": "Malayalam",
    "kn": "Kannada",
}
