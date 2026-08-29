import math


def wilson_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """
    Calculate Wilson score confidence interval.
    Returns (low, high) as proportions.
    """
    if trials == 0:
        return 0.0, 1.0
    
    z_table = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    if confidence not in z_table:
        raise ValueError(f"Unsupported confidence level: {confidence}. Supported values: {list(z_table.keys())}")
    z = z_table[confidence]
    p_hat = successes / trials
    
    denominator = 1 + z * z / trials
    center = (p_hat + z * z / (2 * trials)) / denominator
    adjustment = z * math.sqrt(p_hat * (1 - p_hat) / trials + z * z / (4 * trials * trials)) / denominator
    
    return max(0, center - adjustment), min(1, center + adjustment)
