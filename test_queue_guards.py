"""
Run: python test_queue_guards.py     (no API keys, no network, real job history untouched)

The guards that keep an unattended run from doing damage:
  1. jobs queued for another website are NOT resumed after WP_URL changes
  2. audio is off by default: no Sarvam call however the job was queued
  3. the REAL pipeline hitting a 402 from Gemini pauses the queue (nothing lost)
  4. five systemic failures in a row pause the queue; a temple's own problem does not
"""

import json
import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import httpx

import dashboard.pipeline as pipe
from app.config import settings
from app.tasks import wp_client as wp
from dashboard import jobs

CF = wp.CONTENT_FIELD_KEYS
ENGLISH = "<h3>Shiva Temple</h3>\n\n" + "\n\n".join(
    f"<p>This ancient temple of Lord Shiva stands on the river bank and pilgrims visit it every year. Part {i}.</p>" for i in range(12))


def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        raise SystemExit(1)


def wait(cond, secs=8):
    end = time.time() + secs
    while time.time() < end and not cond():
        time.sleep(0.02)
    return cond()


# --- fake WordPress / providers around the real pipeline ---
written, voiced = [], []
wp.refresh_language_fields = lambda: None
wp.write_all_translations = lambda pid, items: written.append((pid, sorted(items)))
wp.write_title_and_content = lambda pid, lang, title, html: written.append((pid, [lang]))
wp.generate_and_save = lambda text, lang, pid, slug: voiced.append((pid, lang))
pipe._fetch = lambda pid: {"id": pid, "slug": "t", "status": "publish", "acf": {CF["en"]: ENGLISH},
                           "title": {"raw": "Shiva Temple", "rendered": "Shiva Temple"}}
HINDI = "मंदिर है और यहाँ भक्त आते हैं और दर्शन करते हैं "
state = {"mode": "ok"}


def gemini(text, src, tgt):
    if state["mode"] == "402":
        raise httpx.HTTPStatusError(
            "Client error '402 Payment Required' for url 'https://generativelanguage.googleapis.com/v1beta/models/x:generateContent'",
            request=httpx.Request("POST", "https://generativelanguage.googleapis.com"), response=httpx.Response(402))
    if state["mode"] == "401":
        raise httpx.HTTPStatusError(
            "Client error '401 Unauthorized' for url 'https://generativelanguage.googleapis.com/v1beta/models/x'",
            request=httpx.Request("POST", "https://generativelanguage.googleapis.com"), response=httpx.Response(401))
    return (HINDI * (len(text) // len(HINDI) + 1))[: max(8, int(len(text) * 0.9))]


pipe.gtranslate = gemini
jobs._sync_sheet = lambda job: None
jobs._recount = lambda: None
jobs.settings.job_workers = 1

# --- 1. a saved queue from another website must not be resumed ---
jobs._STATE = Path(tempfile.mkdtemp()) / "jobs_state.json"
old = {"operation": "translate", "languages": None, "source": "en", "translate_langs": ["hi"], "audio_langs": [],
       "force": False, "status": "queued", "logs": [], "error": None, "queued_at": "x", "started_at": None, "finished_at": None}
jobs._STATE.write_text(json.dumps({
    "101": {**old, "id": 101, "temple_id": 5001, "temple_title": "Staging temple", "site": "https://some-other-site.example"},
    "102": {**old, "id": 102, "temple_id": 5002, "temple_title": "This site's temple", "site": settings.wp_url},
}), encoding="utf-8")
jobs.start_worker()
check("resume: the job queued for THIS site runs", wait(lambda: jobs.get_job(102)["status"] == "done"))
check("resume: the job queued for ANOTHER site is cancelled, not run",
      jobs.get_job(101)["status"] == "cancelled" and all(pid != 5001 for pid, _ in written))

# --- 2. audio is off by default ---
check("audio is off by default", settings.audio_enabled is False)
j = jobs.enqueue(1, "A", "full", None, "en", translate_langs=["hi"], audio_langs=["en", "hi"])
check("job with audio requested still translates", wait(lambda: jobs.get_job(j)["status"] == "done"))
check("...and makes no recording while audio is off", voiced == [] and any("audio is switched off" in l for l in jobs.get_job(j)["logs"]))
settings.audio_enabled = True
j = jobs.enqueue(2, "B", "audio", None, "en", translate_langs=[], audio_langs=["en"])
check("with AUDIO_ENABLED the same request records", wait(lambda: jobs.get_job(j)["status"] == "done") and voiced == [(2, "en")])
settings.audio_enabled = False

# --- 3. the real pipeline + a real-looking 402 -> pause, job kept ---
state["mode"] = "402"
a = jobs.enqueue(3, "C", "translate", None, "en", translate_langs=["hi"], audio_langs=[])
b = jobs.enqueue(4, "D", "translate", None, "en", translate_langs=["hi"], audio_langs=[])
check("real pipeline: Gemini 402 pauses the queue", wait(lambda: jobs.paused() is not None))
time.sleep(0.3)
check("...names Gemini, keeps both temples waiting, saves nothing wrong",
      jobs.paused()["provider"] == "Gemini" and jobs.get_job(a)["status"] == "queued"
      and jobs.get_job(b)["status"] == "queued" and all(pid not in (3, 4) for pid, _ in written))
state["mode"] = "ok"
jobs.resume()
check("...after top-up + Resume both finish", wait(lambda: jobs.get_job(a)["status"] == "done" and jobs.get_job(b)["status"] == "done"))

# --- 4. failure streak ---
check("a temple's own problem is recognised", jobs._own_problem("This temple has no article to translate from yet - add ...")
      and jobs._own_problem("only 8/9 languages written (kn missing)") and not jobs._own_problem("only 0/9 languages written")
      and not jobs._own_problem("Client error '401 Unauthorized'"))
state["mode"] = "401"
ids = [jobs.enqueue(10 + i, f"T{i}", "translate", None, "en", translate_langs=["hi"], audio_langs=[]) for i in range(8)]
check("5 systemic failures in a row pause the queue", wait(lambda: jobs.paused() is not None, 20))
time.sleep(0.3)
st = [jobs.get_job(i)["status"] for i in ids]
check("...the remaining temples are untouched, not failed", st.count("failed") == 5 and st.count("queued") == 3 and jobs.paused()["provider"] is None)
state["mode"] = "ok"
jobs.resume()
check("...Resume finishes the rest", wait(lambda: all(jobs.get_job(i)["status"] == "done" for i in ids[5:])))

pipe._fetch = lambda pid: {"id": pid, "slug": "t", "status": "publish", "acf": {}, "title": {"raw": "x", "rendered": "x"}}
ids = [jobs.enqueue(30 + i, f"E{i}", "translate", None, None, translate_langs=["hi"], audio_langs=[]) for i in range(7)]
check("7 temples with no article all fail on their own...", wait(lambda: all(jobs.get_job(i)["status"] == "failed" for i in ids), 20))
check("...with a message a person can act on, and WITHOUT pausing the queue",
      jobs.paused() is None and "add its content" in jobs.get_job(ids[0])["error"])
print("\nall queue-guard checks passed")
