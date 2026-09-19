"""Bond pricing/yield math (pure functions, no network, no dates-as-strings)
plus FRED access for the Treasury curve. The math functions take plain
numbers and return plain numbers so tests can reach them without a network
call or a file on disk.

Conventions used throughout unless a function says otherwise:
- `face` is redemption value (e.g. 1000 or 100), `coupon_rate` is the ANNUAL
  coupon rate as a decimal (0.05, not 5).
- `yld` is the ANNUAL yield as a decimal, compounded `freq` times per year.
- `freq` is coupon/compounding periods per year (2 = semiannual, the US
  convention, and the default everywhere).
- `years_to_maturity` must land on a whole number of periods
  (years_to_maturity * freq); these are idealized valuation-on-a-coupon-date
  formulas. Settlement between coupon dates is handled separately by
  `accrued_interest` / `clean_price` / `dirty_price`.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd

DATA_CACHE = Path("data/cache")
OUTPUT = Path("output")

DEFAULT_FREQ = 2


# ---------------------------------------------------------------------------
# Discounting and price
# ---------------------------------------------------------------------------

def discount_factor(yld: float, freq: int, n_periods: float) -> float:
    """PV of $1 received n_periods periods from now, at yld/freq per period."""
    return 1.0 / (1.0 + yld / freq) ** n_periods


def price_from_yield(
    face: float,
    coupon_rate: float,
    yld: float,
    years_to_maturity: float,
    freq: int = DEFAULT_FREQ,
    redemption: float | None = None,
) -> float:
    """PV of the coupon stream plus a redemption payment at maturity.

    `redemption` defaults to `face`; pass a call price to price a bond to a
    call date instead of maturity (yield-to-call uses this).
    """
    if redemption is None:
        redemption = face
    n = round(years_to_maturity * freq)
    coupon = face * coupon_rate / freq
    price = 0.0
    for k in range(1, n + 1):
        cash_flow = coupon + (redemption if k == n else 0.0)
        price += cash_flow * discount_factor(yld, freq, k)
    return price


def current_yield(face: float, coupon_rate: float, price: float) -> float:
    """Annual coupon / price. Differs from YTM because it ignores the
    capital gain or loss between price and redemption value, and ignores
    the time value of the coupons still to come.
    """
    return (face * coupon_rate) / price


# ---------------------------------------------------------------------------
# Yield to maturity / yield to call (bisection — always converges here
# because price is strictly decreasing in yield)
# ---------------------------------------------------------------------------

def solve_yield(
    price: float,
    face: float,
    coupon_rate: float,
    years_to_maturity: float,
    freq: int = DEFAULT_FREQ,
    redemption: float | None = None,
    tol: float = 1e-10,
    max_iter: int = 200,
) -> float:
    """Solve price_from_yield(...) = price for the yield, by bisection."""
    if price <= 0:
        raise ValueError("price must be positive to solve for a yield")

    def f(y: float) -> float:
        return price_from_yield(face, coupon_rate, y, years_to_maturity, freq, redemption) - price

    lo, hi = -0.9 * freq, 10.0  # 1 + lo/freq > 0 required for discounting to be defined
    f_lo, f_hi = f(lo), f(hi)
    if f_lo * f_hi > 0:
        raise ValueError("price is outside the range reachable by any yield in [lo, hi]")

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = f(mid)
        if abs(f_mid) < tol or (hi - lo) / 2 < tol:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


def yield_to_maturity(
    price: float, face: float, coupon_rate: float, years_to_maturity: float, freq: int = DEFAULT_FREQ
) -> float:
    return solve_yield(price, face, coupon_rate, years_to_maturity, freq)


def yield_to_call(
    price: float,
    face: float,
    coupon_rate: float,
    years_to_call: float,
    call_price: float,
    freq: int = DEFAULT_FREQ,
) -> float:
    """Same as YTM, but coupons stop and redemption is `call_price` at the
    call date instead of `face` at maturity.
    """
    return solve_yield(price, face, coupon_rate, years_to_call, freq, redemption=call_price)


# ---------------------------------------------------------------------------
# Duration and convexity
# ---------------------------------------------------------------------------

def macaulay_duration(
    face: float,
    coupon_rate: float,
    yld: float,
    years_to_maturity: float,
    freq: int = DEFAULT_FREQ,
    redemption: float | None = None,
) -> float:
    """Weighted-average time (in years) until you get your money back, each
    cash flow weighted by its share of the bond's present value.
    """
    if redemption is None:
        redemption = face
    n = round(years_to_maturity * freq)
    coupon = face * coupon_rate / freq
    price = price_from_yield(face, coupon_rate, yld, years_to_maturity, freq, redemption)
    weighted_time = 0.0
    for k in range(1, n + 1):
        cash_flow = coupon + (redemption if k == n else 0.0)
        t = k / freq
        weighted_time += t * cash_flow * discount_factor(yld, freq, k)
    return weighted_time / price


def modified_duration(macaulay_dur: float, yld: float, freq: int = DEFAULT_FREQ) -> float:
    """Estimated % price change for a 1.0 (i.e. 100%) move in yield;
    multiply by -100 * delta_yield for the more familiar "% per 1%" framing.
    """
    return macaulay_dur / (1 + yld / freq)


def convexity(
    face: float,
    coupon_rate: float,
    yld: float,
    years_to_maturity: float,
    freq: int = DEFAULT_FREQ,
    redemption: float | None = None,
) -> float:
    """Second-order correction term: modified duration alone is a straight
    line tangent to the (curved) price-yield relationship, and convexity
    measures how much that line underestimates the price for a large move.
    """
    if redemption is None:
        redemption = face
    n = round(years_to_maturity * freq)
    coupon = face * coupon_rate / freq
    price = price_from_yield(face, coupon_rate, yld, years_to_maturity, freq, redemption)
    total = 0.0
    for k in range(1, n + 1):
        cash_flow = coupon + (redemption if k == n else 0.0)
        t = k / freq
        total += cash_flow * discount_factor(yld, freq, k) * t * (t + 1 / freq)
    return total / (price * (1 + yld / freq) ** 2)


def estimate_price_change_pct(mod_duration: float, cvx: float, delta_yield: float) -> float:
    """Duration + convexity estimate of % price change for a yield move of
    `delta_yield` (e.g. 0.01 for +100bp). Compare against a full reprice
    (price_from_yield at yld+delta_yield) to see the approximation error —
    that gap is exactly what convexity is correcting for.
    """
    return -mod_duration * delta_yield + 0.5 * cvx * delta_yield**2


# ---------------------------------------------------------------------------
# Accrued interest, day count conventions, clean/dirty price
# ---------------------------------------------------------------------------

def _days_30_360(d1: date, d2: date) -> int:
    """30/360 (bond basis): every month is treated as 30 days."""
    day1 = min(d1.day, 30)
    day2 = d2.day
    if day1 == 30 and day2 == 31:
        day2 = 30
    return (d2.year - d1.year) * 360 + (d2.month - d1.month) * 30 + (day2 - day1)


def day_count_fraction(
    prev_coupon: date, settlement: date, next_coupon: date, convention: str = "actual/actual"
) -> float:
    """Fraction of the current coupon period that has elapsed as of
    `settlement`. Use "30/360" for corporates and munis, "actual/actual" for
    Treasuries — pass it as a parameter, not a hard-coded assumption.
    """
    if convention == "30/360":
        numerator = _days_30_360(prev_coupon, settlement)
        denominator = _days_30_360(prev_coupon, next_coupon)
    elif convention == "actual/actual":
        numerator = (settlement - prev_coupon).days
        denominator = (next_coupon - prev_coupon).days
    else:
        raise ValueError(f"unknown day count convention: {convention}")
    if denominator == 0:
        raise ValueError("prev_coupon and next_coupon must differ")
    return numerator / denominator


def accrued_interest(
    face: float,
    coupon_rate: float,
    freq: int,
    prev_coupon: date,
    settlement: date,
    next_coupon: date,
    convention: str = "actual/actual",
) -> float:
    """Interest earned by the seller since the last coupon, owed by the
    buyer on top of the quoted (clean) price.
    """
    coupon = face * coupon_rate / freq
    return coupon * day_count_fraction(prev_coupon, settlement, next_coupon, convention)


def clean_price(dirty: float, accrued: float) -> float:
    """The quoted price: what you'd see on a screen, excludes accrued interest."""
    return dirty - accrued


def dirty_price(clean: float, accrued: float) -> float:
    """The price you actually pay at settlement: quoted price plus accrued interest."""
    return clean + accrued


# ---------------------------------------------------------------------------
# FRED access (network — not covered by unit tests)
# ---------------------------------------------------------------------------

# Constant-maturity Treasury series and their maturity in years, used for
# curve charts and the 10y-3mo spread.
TREASURY_SERIES = {
    "DGS1MO": 1 / 12,
    "DGS3MO": 3 / 12,
    "DGS6MO": 6 / 12,
    "DGS1": 1,
    "DGS2": 2,
    "DGS3": 3,
    "DGS5": 5,
    "DGS7": 7,
    "DGS10": 10,
    "DGS20": 20,
    "DGS30": 30,
}


def get_fred_client():
    from dotenv import load_dotenv
    from fredapi import Fred

    load_dotenv()
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError(
            "FRED_API_KEY not set. Copy .env.example to .env and add your key "
            "(free, instant activation at https://fred.stlouisfed.org/docs/api/api_key.html)."
        )
    return Fred(api_key=api_key)


def fetch_series(fred, series_id: str, cache_dir: Path = DATA_CACHE, force: bool = False) -> pd.Series:
    """Fetch a series from FRED, caching to CSV so reruns don't hit the API.
    These are daily series that don't need to be re-pulled every run.
    """
    cache_path = Path(cache_dir) / f"{series_id}.csv"
    if cache_path.exists() and not force:
        return load_cached(series_id, cache_dir)
    s = fred.get_series(series_id)
    s.name = series_id
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    s.to_csv(cache_path)
    return s


def load_cached(series_id: str, cache_dir: Path = DATA_CACHE) -> pd.Series:
    """Load a previously-fetched series from the local cache (no network)."""
    cache_path = Path(cache_dir) / f"{series_id}.csv"
    if not cache_path.exists():
        raise FileNotFoundError(f"No cached data for {series_id} at {cache_path}. Run 02_fetch_curve.py first.")
    s = pd.read_csv(cache_path, index_col=0, parse_dates=True).iloc[:, 0]
    s.name = series_id
    return s


# ---------------------------------------------------------------------------
# Curve shape (pure functions, unit-tested)
# ---------------------------------------------------------------------------

def curve_on_date(series_by_maturity: dict[str, pd.Series], as_of: pd.Timestamp) -> pd.Series:
    """Build a maturity(years) -> yield curve for one date from a dict of
    {series_id: full history Series}, using the last observation on or
    before `as_of` for each maturity (FRED yields aren't published on
    weekends/holidays, so an exact-date lookup would silently drop points).
    """
    points = {}
    for series_id, maturity_years in TREASURY_SERIES.items():
        if series_id not in series_by_maturity:
            continue
        s = series_by_maturity[series_id].dropna()
        s = s[s.index <= as_of]
        if not s.empty:
            points[maturity_years] = s.iloc[-1]
    return pd.Series(points).sort_index()


def curve_spread(long_series: pd.Series, short_series: pd.Series) -> pd.Series:
    """e.g. 10y minus 3mo, aligned on shared dates, positive = normal curve."""
    return (long_series - short_series).dropna()


def classify_curve(curve: pd.Series, flat_band: float = 0.0025) -> str:
    """"normal" / "flat" / "inverted", using the 10-year minus 3-month
    spread (a decimal, e.g. 0.01 = 1 percentage point) — the same pair
    recession-watchers cite. `flat_band` is how close to zero the spread
    can be and still count as "flat" rather than a real normal/inverted
    signal; 25bp is a reasonable default given day-to-day curve noise.
    """
    if 3 / 12 not in curve.index or 10 not in curve.index:
        raise ValueError("classify_curve needs a 3-month (DGS3MO) and 10-year (DGS10) point")
    spread = curve[10] - curve[3 / 12]
    if spread > flat_band:
        return "normal"
    if spread < -flat_band:
        return "inverted"
    return "flat"
