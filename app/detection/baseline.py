from __future__ import annotations

from statistics import median, quantiles


def summarize_baseline(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"samples": 0, "median": None, "p90": None, "p95": None, "range": None}
    ordered = sorted(values)
    if len(ordered) < 2:
        p90 = p95 = ordered[0]
    else:
        cuts = quantiles(ordered, n=20, method="inclusive")
        p90, p95 = cuts[17], cuts[18]
    return {
        "samples": len(ordered),
        "median": median(ordered),
        "p90": p90,
        "p95": p95,
        "range": ordered[-1] - ordered[0],
    }
