"""Chart today's Treasury curve against 1 year ago and 5 years ago, chart
the 10y-3mo spread with recession shading, and flag the current curve
shape. Reads from data/cache/ (run 02_fetch_curve.py first); no network.
"""
import sys

import matplotlib.pyplot as plt
import pandas as pd

from bond_common import OUTPUT, TREASURY_SERIES, classify_curve, curve_on_date, curve_spread, load_cached

MATURITY_LABELS = {
    "DGS1MO": "1mo", "DGS3MO": "3mo", "DGS6MO": "6mo", "DGS1": "1y", "DGS2": "2y",
    "DGS3": "3y", "DGS5": "5y", "DGS7": "7y", "DGS10": "10y", "DGS20": "20y", "DGS30": "30y",
}


def load_all_series() -> dict[str, pd.Series]:
    series = {}
    for series_id in TREASURY_SERIES:
        try:
            series[series_id] = load_cached(series_id)
        except FileNotFoundError as e:
            print(f"[WARN] {e}")
    return series


def plot_curve_comparison(series_by_maturity: dict[str, pd.Series]) -> None:
    latest_date = max(s.dropna().index[-1] for s in series_by_maturity.values())
    snapshots = {
        f"Today ({latest_date.date()})": latest_date,
        "1 year ago": latest_date - pd.DateOffset(years=1),
        "5 years ago": latest_date - pd.DateOffset(years=5),
    }

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for label, as_of in snapshots.items():
        curve = curve_on_date(series_by_maturity, as_of)
        ax.plot(curve.index, curve.values * 100, marker="o", label=label)

    ax.set_xlabel("Maturity (years)")
    ax.set_ylabel("Yield (%)")
    ax.set_title("Treasury yield curve: today vs. 1yr ago vs. 5yr ago")
    ax.set_xscale("log")
    ax.set_xticks(list(TREASURY_SERIES.values()))
    ax.set_xticklabels(list(MATURITY_LABELS.values()))
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "curve_comparison.png", dpi=150)
    plt.close(fig)

    current_curve = curve_on_date(series_by_maturity, latest_date)
    shape = classify_curve(current_curve)
    print(f"[OK] wrote {OUTPUT / 'curve_comparison.png'}")
    print(f"Current curve shape: {shape} (10y - 3mo = {(current_curve[10] - current_curve[3/12]) * 100:.2f}pp)")


def plot_spread_and_recessions(ten_year: pd.Series, three_month: pd.Series, usrec: pd.Series) -> None:
    # ten_year/three_month are cached straight from FRED, already in
    # percentage-point units (4.94 means 4.94%), so their difference is
    # already a percentage-point spread — no further scaling needed.
    spread = curve_spread(ten_year, three_month)

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(spread.index, spread.values, color="tab:blue", linewidth=0.8)
    ax.axhline(0, color="black", linewidth=0.8)

    recession_on = usrec.reindex(spread.index, method="ffill").fillna(0)
    in_recession = recession_on.astype(int) == 1
    ax.fill_between(spread.index, spread.min(), spread.max(), where=in_recession, color="grey", alpha=0.3)

    ax.set_ylabel("10y - 3mo spread (pp)")
    ax.set_title("10-year minus 3-month Treasury spread, with NBER recessions shaded")
    ax.grid(alpha=0.3)
    fig.tight_layout()

    OUTPUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT / "spread_recessions.png", dpi=150)
    plt.close(fig)
    print(f"[OK] wrote {OUTPUT / 'spread_recessions.png'}")


def main() -> int:
    series_by_maturity = load_all_series()
    if "DGS10" not in series_by_maturity or "DGS3MO" not in series_by_maturity:
        print("[FAIL] need DGS10 and DGS3MO cached. Run 02_fetch_curve.py first.")
        return 1

    plot_curve_comparison(series_by_maturity)

    try:
        usrec = load_cached("USREC")
    except FileNotFoundError as e:
        print(f"[WARN] {e} — skipping recession-shaded spread chart.")
        return 0

    plot_spread_and_recessions(series_by_maturity["DGS10"], series_by_maturity["DGS3MO"], usrec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
