"""
Background work: slow tasks run off the request path, so pages stay fast.

The slow task today is LIME (2,000 model calls per employee): asking for it starts a job and answers at once; the
page asks again until the result is ready. Results are kept by a key that includes the model version and the
exact record, so a corrected record or a new model never gets an old answer.

One worker thread inside the API process: enough for one organisation's HR team, and nothing extra to install or
run. A bigger deployment would swap this module for a task queue (e.g. Redis with RQ or Celery) behind the same
three functions.
"""
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

KEEP_RESULTS = 500  # finished results kept in memory (the oldest are dropped first)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="meritlens-job")
_lock = threading.Lock()
_jobs: "OrderedDict[str, dict]" = OrderedDict()  # key -> {"status": "running" | "done" | "error", "result", "error"}


def _run(key: str, work) -> None:
    try:
        result = work()
    except Exception as error:  # noqa: BLE001 - the page shows the message; the worker keeps going
        with _lock:
            _jobs[key] = {"status": "error", "error": str(error) or error.__class__.__name__}
        return
    with _lock:
        _jobs[key] = {"status": "done", "result": result}
        _jobs.move_to_end(key)
        while len(_jobs) > KEEP_RESULTS:
            _jobs.popitem(last=False)


def submit(key: str, work) -> dict:
    """Start `work()` in the background unless the same key is already running or done. Returns its state."""
    with _lock:
        state = _jobs.get(key)
        if state is not None and state["status"] != "error":
            return dict(state)
        _jobs[key] = {"status": "running"}
    _executor.submit(_run, key, work)
    return {"status": "running"}


def state(key: str) -> dict | None:
    """The job's state, or None if it was never started (or its result was dropped)."""
    with _lock:
        found = _jobs.get(key)
        return dict(found) if found is not None else None


def clear() -> None:
    """Forget every result (used when a different model version goes live, and by the tests)."""
    with _lock:
        for key in [k for k, v in _jobs.items() if v["status"] != "running"]:
            del _jobs[key]
