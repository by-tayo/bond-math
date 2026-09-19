"""Rate shock table: for a set of bonds at different maturities, show the
price change at -200/-100/+100/+200bp using both the duration+convexity
estimate and a full reprice, so the gap between them is visible. No
network access.
"""
import sys

import pandas as pd

from bond_common import (
    OUTPUT,
    convexity,
    estimate_price_change_pct,
    macaulay_duration,
    modified_duration,
    price_from_yield,
)

BONDS = [
    {"label": "2yr", "face": 1000, "coupon_rate": 0.045, "years_to_maturity": 2, "yld": 0.045},
    {"label": "5yr", "face": 1000, "coupon_rate": 0.045, "years_to_maturity": 5, "yld": 0.045},
    {"label": "10yr", "face": 1000, "coupon_rate": 0.045, "years_to_maturity": 10, "yld": 0.045},
    {"label": "30yr", "face": 1000, "coupon_rate": 0.045, "years_to_maturity": 30, "yld": 0.045},
]

SHOCKS_BP = [-200, -100, 100, 200]


def main() -> int:
    rows = []
    for bond in BONDS:
        face, coupon_rate, ytm, years = bond["face"], bond["coupon_rate"], bond["yld"], bond["years_to_maturity"]
        price = price_from_yield(face, coupon_rate, ytm, years)
        mac_dur = macaulay_duration(face, coupon_rate, ytm, years)
        mod_dur = modified_duration(mac_dur, ytm)
        cvx = convexity(face, coupon_rate, ytm, years)

        for shock_bp in SHOCKS_BP:
            delta = shock_bp / 10_000
            est_pct = estimate_price_change_pct(mod_dur, cvx, delta)
            full_price = price_from_yield(face, coupon_rate, ytm + delta, years)
            full_pct = full_price / price - 1
            rows.append(
                {
                    "bond": bond["label"],
                    "shock_bp": shock_bp,
                    "duration_convexity_est_%": round(est_pct * 100, 3),
                    "full_reprice_%": round(full_pct * 100, 3),
                    "gap_%": round((full_pct - est_pct) * 100, 4),
                }
            )

    df = pd.DataFrame(rows)
    print(df.to_string(index=False))

    plus_100 = df[df["shock_bp"] == 100].set_index("bond")["full_reprice_%"]
    if not (plus_100.loc["30yr"] < plus_100.loc["10yr"] < plus_100.loc["5yr"] < plus_100.loc["2yr"]):
        print("[FAIL] longer maturities should lose more at +100bp — check for a duration sign error")
        return 1
    print("\n[OK] longer maturities lose more at +100bp, as expected")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT / "rate_shock.csv", index=False)
    print(f"[OK] wrote {OUTPUT / 'rate_shock.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
