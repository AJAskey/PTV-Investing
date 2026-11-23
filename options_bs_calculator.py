#!/usr/bin/env python3
"""Black-Scholes European option pricing calculator."""

import math


def normal_cdf(x: float) -> float:
    """Cumulative distribution function for the standard normal distribution."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def calculate_option_price(
    S: float,
    K: float,
    DTE: float,
    r: float,
    iv: float,
    option_type: str = "call",
    q: float = 0.0,
) -> float:
    """
    Calculate European option price using Black-Scholes-Merton.

    S: Stock price (> 0)
    K: Strike price (> 0)
    DTE: Days to expiration
    r: Risk-free rate (e.g. 0.05 for 5%)
    iv: Implied volatility (e.g. 0.20 for 20%)
    option_type: 'call' or 'put'
    q: Continuous dividend yield (e.g. 0.015 for 1.5%)
    """
    opt = option_type.lower()
    if opt not in ("call", "put"):
        raise ValueError(f"Invalid option_type {option_type!r}; expected 'call' or 'put'.")
    if S <= 0 or K <= 0:
        raise ValueError("Stock price (S) and strike price (K) must be positive.")
    if iv < 0:
        raise ValueError("Implied volatility (iv) cannot be negative.")

    if DTE <= 0:
        return max(0.0, S - K) if opt == "call" else max(0.0, K - S)

    T = DTE / 365.0
    disc_S = S * math.exp(-q * T)
    disc_K = K * math.exp(-r * T)

    if iv == 0:
        return max(0.0, disc_S - disc_K) if opt == "call" else max(0.0, disc_K - disc_S)

    sigma_sqrt_t = iv * math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * (iv ** 2)) * T) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t

    if opt == "call":
        price = disc_S * normal_cdf(d1) - disc_K * normal_cdf(d2)
    else:
        price = disc_K * normal_cdf(-d2) - disc_S * normal_cdf(-d1)

    return max(0.0, price)


if __name__ == "__main__":
    S = 149.53
    K = 110.0
    DTE = 30
    r = 0.05
    iv = 0.86152

    call_price = calculate_option_price(S, K, DTE, r, iv, option_type="call")
    put_price = calculate_option_price(S, K, DTE, r, iv, option_type="put")

    print(f"Call Option Price: {call_price:.2f}")
    print(f"Put Option Price: {put_price:.2f}")