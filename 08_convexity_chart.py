"""The chart the build plan explicitly asks for: modified duration's
price-change estimate is close for a small yield move and visibly off for
a large one, because it's a straight line tangent to a curve. This plots
the actual price-yield relationship against the duration-only (linear) and
duration+convexity (quadratic) estimates, so the gap is visible instead of
just a number in a table. Same bond as 01_price_bond.py. No network.
"""
import numpy as np
import matplotlib.pyplot as plt

from bond_common import (
    OUTPUT,
    convexity,
    estimate_price_change_pct,
    macaulay_duration,
    modified_duration,
    price_from_yield,
)

FACE = 1000
COUPON_RATE = 0.045
YEARS_TO_MATURITY = 10
BASE_YIELD = 0.05
SHOCK_RANGE_BP = 300  # plot +/- this many basis points around the base yield


def main() -> None:
    base_price = price_from_yield(FACE, COUPON_RATE, BASE_YIELD, YEARS_TO_MATURITY)
    mac_dur = macaulay_duration(FACE, COUPON_RATE, BASE_YIELD, YEARS_TO_MATURITY)
    mod_dur = modified_duration(mac_dur, BASE_YIELD)
    cvx = convexity(FACE, COUPON_RATE, BASE_YIELD, YEARS_TO_MATURITY)

    deltas = np.linspace(-SHOCK_RANGE_BP / 10_000, SHOCK_RANGE_BP / 10_000, 121)
    full_reprice = [price_from_yield(FACE, COUPON_RATE, BASE_YIELD + d, YEARS_TO_MATURITY) for d in deltas]
    duration_only = [base_price * (1 - mod_dur * d) for d in deltas]
    duration_plus_convexity = [base_price * (1 + estimate_price_change_pct(mod_dur, cvx, d)) for d in deltas]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.plot(deltas * 10_000, full_reprice, color="black", linewidth=2.5, label="Full reprice (actual)")
    ax.plot(deltas * 10_000, duration_only, "--", color="tab:red", label="Duration-only estimate (tangent line)")
    ax.plot(deltas * 10_000, duration_plus_convexity, ":", color="tab:blue", linewidth=2, label="Duration + convexity estimate")
    ax.axvline(0, color="grey", linewidth=0.6)
    ax.axhline(base_price, color="grey", linewidth=0.6)
    ax.set_xlabel("Yield change from base (bp)")
    ax.set_ylabel("Price ($)")
    ax.set_title(
        f"{COUPON_RATE:.1%} coupon, {YEARS_TO_MATURITY}yr bond at {BASE_YIELD:.1%}: "
        "why duration alone understates the price for a big move"
    )
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "convexity_gap.png", dpi=150)
    print(f"[OK] wrote {OUTPUT / 'convexity_gap.png'}")

    at_300bp = deltas[-1]
    actual = price_from_yield(FACE, COUPON_RATE, BASE_YIELD + at_300bp, YEARS_TO_MATURITY)
    dur_only_est = base_price * (1 - mod_dur * at_300bp)
    print(f"At +{SHOCK_RANGE_BP}bp: actual price ${actual:,.2f}, duration-only estimate ${dur_only_est:,.2f} "
          f"(off by ${dur_only_est - actual:,.2f})")


if __name__ == "__main__":
    main()
