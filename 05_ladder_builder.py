"""Bond ladder builder: split an amount across evenly-spaced maturities,
price each rung off today's Treasury curve, and show the income stream
plus the reinvestment schedule as rungs mature. Reads data/cache/ (run
02_fetch_curve.py first); no network.
"""
import sys

import pandas as pd

from bond_common import OUTPUT, curve_on_date, interpolate_curve, load_cached

TOTAL_AMOUNT = 100_000
NUM_RUNGS = 5
START_MATURITY_YEARS = 2
RUNG_SPACING_YEARS = 2


def build_ladder(curve: pd.Series, total_amount: float, num_rungs: int, start_years: float, spacing_years: float):
    amount_per_rung = total_amount / num_rungs
    rungs = []
    for i in range(num_rungs):
        maturity = start_years + i * spacing_years
        yld = interpolate_curve(curve, maturity)
        rungs.append(
            {
                "rung": i + 1,
                "maturity_years": maturity,
                "face": amount_per_rung,
                "yield": yld,
                "annual_income": amount_per_rung * yld,
            }
        )
    return pd.DataFrame(rungs)


def main() -> int:
    try:
        dgs = {sid: load_cached(sid) for sid in ["DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS3", "DGS5", "DGS7", "DGS10", "DGS20", "DGS30"]}
    except FileNotFoundError as e:
        print(f"[FAIL] {e}")
        return 1

    latest_date = max(s.dropna().index[-1] for s in dgs.values())
    curve = curve_on_date(dgs, latest_date)

    ladder = build_ladder(curve, TOTAL_AMOUNT, NUM_RUNGS, START_MATURITY_YEARS, RUNG_SPACING_YEARS)
    print(f"Ladder as of {latest_date.date()}: ${TOTAL_AMOUNT:,.0f} across {NUM_RUNGS} rungs, "
          f"{START_MATURITY_YEARS}yr to {START_MATURITY_YEARS + (NUM_RUNGS - 1) * RUNG_SPACING_YEARS}yr, "
          f"{RUNG_SPACING_YEARS}yr apart\n")

    display = ladder.copy()
    display["yield"] = (display["yield"] * 100).round(3).astype(str) + "%"
    display["face"] = display["face"].map(lambda v: f"${v:,.0f}")
    display["annual_income"] = display["annual_income"].map(lambda v: f"${v:,.2f}")
    print(display.to_string(index=False))

    total_income = ladder["annual_income"].sum()
    print(f"\nTotal annual income across the ladder: ${total_income:,.2f} "
          f"({total_income / TOTAL_AMOUNT:.3%} blended yield)")

    print("\nReinvestment schedule (each rung, at maturity, rolls into a new "
          f"{START_MATURITY_YEARS + (NUM_RUNGS - 1) * RUNG_SPACING_YEARS}yr rung at that day's long end):")
    for _, row in ladder.iterrows():
        print(f"  Year {row['maturity_years']:.0f}: rung {int(row['rung'])} (${row['face']:,.0f}) matures and rolls forward")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    ladder.to_csv(OUTPUT / "ladder.csv", index=False)
    print(f"\n[OK] wrote {OUTPUT / 'ladder.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
