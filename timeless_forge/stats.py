import math


def wilson_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """
    Calculate Wilson score confidence interval.
    Returns (low, high) as proportions.
    """
    if trials == 0:
        return 0.0, 1.0
    
    z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%
    p_hat = successes / trials
    
    denominator = 1 + z * z / trials
    center = (p_hat + z * z / (2 * trials)) / denominator
    adjustment = z * math.sqrt(p_hat * (1 - p_hat) / trials + z * z / (4 * trials * trials)) / denominator
    
    return max(0, center - adjustment), min(1, center + adjustment)
