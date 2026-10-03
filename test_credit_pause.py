"""
Run: python test_credit_pause.py      (no API keys, no network, real job history untouched)

When a provider runs out of credit the queue must PAUSE and keep the job,
not mark temple after temple "failed" -- and must not pause on ordinary failures.
"""

import sys
import tempfile
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from dashboard import jobs

jobs._STATE = Path(tempfile.mkdtemp()) / "jobs_state.json"  # never the real queue file
jobs._sync_sheet = lambda job: None
jobs._recount = lambda: None


def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name)
    if not ok:
        raise SystemExit(1)


# --- what counts as "out of credit" ---
GEMINI_402 = "Client error '402 Payment Required' for url 'https://generativelanguage.googleapis.com/v1beta/models/x'"
check("Gemini 402 -> Gemini", jobs.out_of_credit(GEMINI_402) == "Gemini")
check("Sarvam out-of-credit text -> Sarvam",
      jobs.out_of_credit('[ta] AUDIO FAILED: 403 from Sarvam TTS (lang=ta-IN): {"error":"Insufficient credits"}') == "Sarvam")
check("429 on every language, nothing written -> paused",
      jobs.out_of_credit("[ta] TRANSLATE FAILED: 429 Too Many Requests generativelanguage\nonly 0/9 languages written") == "Gemini")
check("a lone 429 that still wrote languages is NOT credit",
      jobs.out_of_credit("[ta] TRANSLATE FAILED: 429 Too Many Requests\nonly 8/9 languages written") is None)
check("the pipeline's own 'check credits/quota' hint is NOT credit",
      jobs.out_of_credit("only 6/9 languages written (kn missing) - check the translation provider's credits/quota") is None)
check("a quality-check failure is NOT credit", jobs.out_of_credit("kn: runaway repetition") is None)

# --- the queue itself ---
calls = []
credit = {"left": False}


def fake_process(temple_id, *a, log=print, **kw):
    calls.append(temple_id)
    if not credit["left"]:
        log(f"[ta] TRANSLATE FAILED: {GEMINI_402}")
        raise RuntimeError("only 0/9 languages written (all missing)")
    log("✓ complete")


jobs.process_temple = fake_process
jobs.settings.job_workers = 1
jobs.start_worker()


def wait(cond, secs=5):
    end = time.time() + secs
    while time.time() < end and not cond():
        time.sleep(0.02)
    return cond()


a = jobs.enqueue(1, "Temple A", "translate", None, None)
b = jobs.enqueue(2, "Temple B", "translate", None, None)
check("queue pauses on the credit error", wait(lambda: jobs.paused() is not None))
time.sleep(0.3)
check("paused: named provider is Gemini", jobs.paused()["provider"] == "Gemini")
check("the failed temple went back in the queue, not 'failed'", jobs.get_job(a)["status"] == "queued")
check("the next temple was NOT attempted while paused", calls == [1])
check("both temples still count as waiting", jobs.queue_depth() == 2)

credit["left"] = True
jobs.resume()
check("after Resume both temples finish", wait(lambda: jobs.get_job(a)["status"] == "done" and jobs.get_job(b)["status"] == "done"))
check("pause cleared", jobs.paused() is None)

c = jobs.enqueue(3, "Temple C", "translate", None, None)
jobs.process_temple = lambda *a, log=print, **kw: (_ for _ in ()).throw(RuntimeError("kn: runaway repetition"))
check("an ordinary failure is just 'failed'", wait(lambda: jobs.get_job(c)["status"] == "failed"))
check("...and does not pause the queue", jobs.paused() is None)
print("\nall credit-pause checks passed")
