from __future__ import annotations

from math import sqrt


def wilson_interval(wins: float, games: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if games <= 0:
        return 0.0, 0.0
    p = wins / games
    denominator = 1 + z * z / games
    center = (p + z * z / (2 * games)) / denominator
    margin = z * sqrt((p * (1 - p) + z * z / (4 * games)) / games) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)
