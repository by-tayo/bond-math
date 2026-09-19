"""Fee drag calculator: how much a fund's expense ratio costs you over
30 years, compared side by side at a low fee and a high fee. No network.
"""
import sys

import matplotlib.pyplot as plt

from bond_common import OUTPUT, future_value_path_with_fees, future_value_with_fees

STARTING_AMOUNT = 10_000
ANNUAL_CONTRIBUTION = 6_000
GROSS_RETURN = 0.07
YEARS = 30
LOW_FEE = 0.0003   # 0.03%, a typical broad-market index fund
HIGH_FEE = 0.0075  # 0.75%, a typical actively-managed fund


def plot_growth(low_fee_path: list[float], high_fee_path: list[float]) -> None:
    years = list(range(len(low_fee_path)))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(years, low_fee_path, color="tab:green", linewidth=2, label=f"{LOW_FEE:.2%} expense ratio")
    ax.plot(years, high_fee_path, color="tab:red", linewidth=2, label=f"{HIGH_FEE:.2%} expense ratio")
    ax.fill_between(years, low_fee_path, high_fee_path, color="tab:red", alpha=0.15, label="Fee drag")
    ax.set_xlabel("Year")
    ax.set_ylabel("Account value ($)")
    # Escape $ so matplotlib's mathtext parser doesn't treat "$X, $Y" as a math span.
    ax.set_title(
        f"Fee drag: \\${STARTING_AMOUNT:,.0f} start, \\${ANNUAL_CONTRIBUTION:,.0f}/yr, "
        f"{GROSS_RETURN:.0%} gross return"
    )
    ax.legend()
    ax.grid(alpha=0.3)
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:,.0f}")
    fig.tight_layout()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "fee_drag_growth.png", dpi=150)
    plt.close(fig)
    print(f"[OK] wrote {OUTPUT / 'fee_drag_growth.png'}")


def main() -> int:
    low_fee_path = future_value_path_with_fees(STARTING_AMOUNT, ANNUAL_CONTRIBUTION, GROSS_RETURN, LOW_FEE, YEARS)
    high_fee_path = future_value_path_with_fees(STARTING_AMOUNT, ANNUAL_CONTRIBUTION, GROSS_RETURN, HIGH_FEE, YEARS)
    low_fee_value, high_fee_value = low_fee_path[-1], high_fee_path[-1]
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
        f.write("year,low_fee_value,high_fee_value\n")
        for year, (low, high) in enumerate(zip(low_fee_path, high_fee_path)):
            f.write(f"{year},{low:.2f},{high:.2f}\n")
    print(f"[OK] wrote {OUTPUT / 'fee_drag.csv'}")

    plot_growth(low_fee_path, high_fee_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
