"""Worked example: price a bond, solve its yield, and show what a 1%
rate move does to it. No network access — everything here comes from
bond_common.py's pure math. This is the example quoted in the README.
"""
from bond_common import (
    convexity,
    estimate_price_change_pct,
    macaulay_duration,
    modified_duration,
    price_from_yield,
    yield_to_maturity,
)

FACE = 1000
COUPON_RATE = 0.045
YEARS_TO_MATURITY = 10
MARKET_YIELD = 0.05


def main() -> None:
    price = price_from_yield(FACE, COUPON_RATE, MARKET_YIELD, YEARS_TO_MATURITY)
    ytm = yield_to_maturity(price, FACE, COUPON_RATE, YEARS_TO_MATURITY)
    mac_dur = macaulay_duration(FACE, COUPON_RATE, MARKET_YIELD, YEARS_TO_MATURITY)
    mod_dur = modified_duration(mac_dur, MARKET_YIELD)
    cvx = convexity(FACE, COUPON_RATE, MARKET_YIELD, YEARS_TO_MATURITY)

    print(f"Bond: {COUPON_RATE:.2%} coupon, {YEARS_TO_MATURITY}yr maturity, semiannual, ${FACE:,.0f} face")
    print(f"Market yield: {MARKET_YIELD:.2%}")
    print(f"Price: ${price:,.2f}")
    print(f"Yield to maturity (solved back from price): {ytm:.4%}")
    print(f"Macaulay duration: {mac_dur:.3f} years")
    print(f"Modified duration: {mod_dur:.3f}")
    print(f"Convexity: {cvx:.3f}")

    print("\nIf rates rise 1% (+100bp):")
    est_pct = estimate_price_change_pct(mod_dur, cvx, 0.01)
    full_price = price_from_yield(FACE, COUPON_RATE, MARKET_YIELD + 0.01, YEARS_TO_MATURITY)
    full_pct = full_price / price - 1
    print(f"  Duration+convexity estimate: {est_pct:+.3%}  (${price * est_pct:+,.2f})")
    print(f"  Full reprice:                {full_pct:+.3%}  (${full_price - price:+,.2f})")
    print(f"  New price (full reprice): ${full_price:,.2f}")


if __name__ == "__main__":
    main()
