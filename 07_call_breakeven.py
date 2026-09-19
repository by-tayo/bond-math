"""Breakeven for a call: how long you must hold a callable bond, bought at
a premium for its above-market coupon, before the extra coupon income
recoups what you lose if it's called away at par (or at a call price).
This is a cash-flow approximation, not a discounted-cashflow one — see
docs/methodology.md for what it leaves out. No network.
"""
import sys

from bond_common import call_breakeven_years

FACE = 1000
CALLABLE_COUPON_RATE = 0.065   # above-market coupon that makes the bond worth calling
ALT_COUPON_RATE = 0.05         # a comparable non-callable bond, priced at par today
PRICE_PAID = 1080              # premium paid for the higher coupon
CALL_PRICE = 1020              # what you get back if it's called


def main() -> int:
    extra_annual_coupon = (CALLABLE_COUPON_RATE - ALT_COUPON_RATE) * FACE
    breakeven = call_breakeven_years(PRICE_PAID, CALL_PRICE, extra_annual_coupon)

    print(f"Callable bond: {CALLABLE_COUPON_RATE:.2%} coupon, bought at ${PRICE_PAID:,.0f}, callable at ${CALL_PRICE:,.0f}")
    print(f"Alternative: a comparable non-callable bond at {ALT_COUPON_RATE:.2%}, priced at par")
    print(f"Extra annual coupon income: ${extra_annual_coupon:,.2f}")
    print(f"Premium at risk if called: ${PRICE_PAID - CALL_PRICE:,.2f}")

    if breakeven is None:
        print("\nNo breakeven: the premium is never recouped (or there's no premium at risk).")
    else:
        print(f"\nBreakeven: {breakeven:.2f} years of extra coupon income needed to recoup the premium.")
        print("Hold past that point and being called is a net gain over the alternative; "
              "called before it, and it's a net loss.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
