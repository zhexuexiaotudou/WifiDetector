from __future__ import annotations


def counter_delta(previous: int | None, current: int | None) -> int | None:
    if previous is None or current is None:
        return None
    if current < previous:
        return None
    return current - previous
