"""Self-check for job cancellation. Run: python check_cancel.py

Covers the deadlock that shipped once: cancel() held _lock and called _save(),
which takes _lock itself. threading.Lock is not reentrant, so the call hung
forever holding the lock and wedged every worker. Anything that hangs here
fails the check via the watchdog rather than blocking the run.
"""
import os, threading
os.environ["PILGRIM_NO_WORKER"] = "1"
from dashboard import jobs

def with_timeout(fn, secs=5):
    box = {}
    t = threading.Thread(target=lambda: box.setdefault("r", fn()), daemon=True)
    t.start(); t.join(secs)
    assert not t.is_alive(), "cancel() hung -- lock reentrancy regression"
    return box.get("r")

a = jobs.enqueue(1, "A", "translate", None, None)
b = jobs.enqueue(2, "B", "translate", None, None)
c = jobs.enqueue(3, "C", "translate", None, None)

# a queued job cancels outright
assert with_timeout(lambda: jobs.cancel(a)) == "cancelled"
assert jobs._jobs[a]["status"] == "cancelled"
assert jobs.is_cancelled(a)

# a running job is cancelled cooperatively, not forced
jobs._jobs[b]["status"] = "running"
assert with_timeout(lambda: jobs.cancel(b)) == "stopping"
assert jobs._jobs[b]["status"] == "running", "must not fake a stop it cannot force"
assert jobs.is_cancelled(b)

# a finished job reports its state and is not resurrected
jobs._jobs[c]["status"] = "done"
assert with_timeout(lambda: jobs.cancel(c)) == "done"
assert not jobs.is_cancelled(c)

assert with_timeout(lambda: jobs.cancel(999999)) == "not found"

# cancel_all covers queued + running only
d = jobs.enqueue(4, "D", "translate", None, None)
jobs._jobs[d]["status"] = "running"
e = jobs.enqueue(5, "E", "translate", None, None)
r = with_timeout(lambda: jobs.cancel_all())
assert r["cancelled"] >= 1 and r["stopping"] >= 1, r
assert jobs._jobs[e]["status"] == "cancelled"
assert jobs._jobs[c]["status"] == "done", "cancel_all must not touch finished jobs"

# the lock is genuinely free afterwards
assert jobs._lock.acquire(timeout=2), "lock still held -- deadlock"
jobs._lock.release()
print("cancel self-check OK")
