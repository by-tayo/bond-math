"""Pull the constant-maturity Treasury series plus USREC (for recession
shading) from FRED and cache them to data/cache/. Daily series — no need
to re-run this more than once a day.
"""
import sys

from bond_common import TREASURY_SERIES, fetch_series, get_fred_client


def main() -> int:
    try:
        fred = get_fred_client()
    except RuntimeError as e:
        print(f"[FAIL] {e}")
        return 1

    for series_id in list(TREASURY_SERIES) + ["USREC"]:
        s = fetch_series(fred, series_id)
        print(f"[OK] {series_id}: {len(s)} observations, most recent {s.dropna().index[-1].date()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
