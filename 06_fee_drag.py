"""Fee drag calculator: how much a fund's expense ratio costs you over
30 years, compared side by side at a low fee and a high fee. No network.
"""
import sys

from bond_common import OUTPUT, future_value_with_fees

STARTING_AMOUNT = 10_000
ANNUAL_CONTRIBUTION = 6_000
GROSS_RETURN = 0.07
YEARS = 30
LOW_FEE = 0.0003   # 0.03%, a typical broad-market index fund
HIGH_FEE = 0.0075  # 0.75%, a typical actively-managed fund


def main() -> int:
    low_fee_value = future_value_with_fees(STARTING_AMOUNT, ANNUAL_CONTRIBUTION, GROSS_RETURN, LOW_FEE, YEARS)
    high_fee_value = future_value_with_fees(STARTING_AMOUNT, ANNUAL_CONTRIBUTION, GROSS_RETURN, HIGH_FEE, YEARS)
    difference = low_fee_value - high_fee_value

    print(f"${STARTING_AMOUNT:,.0f} starting, ${ANNUAL_CONTRIBUTION:,.0f}/yr contribution, "
          f"{GROSS_RETURN:.0%} assumed gross return, {YEARS} years\n")
    print(f"  At {LOW_FEE:.2%} expense ratio:  ${low_fee_value:,.2f}")
    print(f"  At {HIGH_FEE:.2%} expense ratio:  ${high_fee_value:,.2f}")
    print(f"\n  Fee drag over {YEARS} years: ${difference:,.2f} ({difference / low_fee_value:.1%} of the low-fee ending value)")

    if difference <= 0:
        print("[FAIL] higher fee should always produce a lower ending value")
        return 1

    OUTPUT.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT / "fee_drag.csv", "w") as f:
        f.write("expense_ratio,ending_value\n")
        f.write(f"{LOW_FEE},{low_fee_value:.2f}\n")
        f.write(f"{HIGH_FEE},{high_fee_value:.2f}\n")
    print(f"\n[OK] wrote {OUTPUT / 'fee_drag.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
