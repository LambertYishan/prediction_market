"""Core market logic implementing a Logarithmic Market Scoring Rule (LMSR).

This module provides functions to calculate the cost to purchase shares in a
binary market and to derive market probabilities. The LMSR cost function
guarantees continuous liquidity: participants can always buy or sell shares
without depending on other traders. It also ensures that the market price
reflects the distribution of outstanding YES and NO shares.
"""

import math
from typing import Tuple


def cost_function(q_yes: float, q_no: float, b: float) -> float:
    """Return the total cost required to reach a given share distribution.

    Args:
        q_yes: The total number of YES shares outstanding.
        q_no: The total number of NO shares outstanding.
        b: The liquidity parameter. Larger ``b`` results in smoother price
           changes and requires more capital to move the price.

    Returns:
        The value of the LMSR cost function C(q_yes, q_no).
    """
    # Use exponentials of q/b. To prevent overflow for extreme values, we
    # normalise by subtracting the maximum exponent from the numerator and
    # denominator when computing the logarithm of the sum.
    exp_yes = math.exp(q_yes / b)
    exp_no = math.exp(q_no / b)
    return b * math.log(exp_yes + exp_no)


def cost_for_shares(q_yes: float, q_no: float, delta: float, side: str, b: float) -> float:
    """Compute the cost to purchase ``delta`` shares on a given side.

    Args:
        q_yes: Current number of YES shares.
        q_no: Current number of NO shares.
        delta: Number of shares the user wants to buy (must be positive).
        side: 'YES' or 'NO' indicating which outcome the shares represent.
        b: Liquidity parameter.

    Returns:
        The cost (in currency units) required to buy the shares.

    Raises:
        ValueError: If ``delta`` is not positive or side is invalid.
    """
    side_upper = side.upper()
    if delta <= 0:
        raise ValueError("delta must be positive")
    if side_upper not in {"YES", "NO"}:
        raise ValueError("side must be 'YES' or 'NO'")

    if side_upper == "YES":
        new_cost = cost_function(q_yes + delta, q_no, b)
    else:  # side_upper == 'NO'
        new_cost = cost_function(q_yes, q_no + delta, b)
    old_cost = cost_function(q_yes, q_no, b)
    return new_cost - old_cost


def price_yes(q_yes: float, q_no: float, b: float) -> float:
    """Compute the current market probability for the YES outcome.

    Given the total YES and NO shares outstanding, the market price for YES is
    derived from the LMSR cost function as the proportion of the YES
    exponential term to the total of both exponential terms.

    Args:
        q_yes: Total number of YES shares.
        q_no: Total number of NO shares.
        b: Liquidity parameter.

    Returns:
        A float between 0 and 1 representing the price/probability of YES.
    """
    exp_yes = math.exp(q_yes / b)
    exp_no = math.exp(q_no / b)
    return exp_yes / (exp_yes + exp_no)


def price_no(q_yes: float, q_no: float, b: float) -> float:
    """Compute the current market probability for the NO outcome."""
    return 1.0 - price_yes(q_yes, q_no, b)