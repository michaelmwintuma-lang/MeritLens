"""
Slowing down password guessing from one place. Each account is already locked after 5 wrong passwords in a row, but
that alone would let someone lock HR or Finance out on purpose, or try a few passwords against every account. So the
failed sign-ins from each network address are also counted: after FAILURES in WINDOW_MINUTES, that address must wait
(HTTP 429) before trying again, whichever accounts it tries. Kept in memory: a restart clears it.
"""
import time
from collections import defaultdict, deque

FAILURES = 20
WINDOW_MINUTES = 15
_failures: dict[str, deque] = defaultdict(deque)


def _recent(address: str) -> deque:
    attempts, cutoff = _failures[address], time.monotonic() - WINDOW_MINUTES * 60
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


def blocked(address: str) -> bool:
    return len(_recent(address)) >= FAILURES


def failed(address: str) -> None:
    _recent(address).append(time.monotonic())


def clear() -> None:
    _failures.clear()
