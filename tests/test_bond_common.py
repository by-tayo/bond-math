from datetime import date

import pytest

import pandas as pd

from bond_common import (
    accrued_interest,
    call_breakeven_years,
    classify_curve,
    clean_price,
    convexity,
    current_yield,
    day_count_fraction,
    dirty_price,
    discount_factor,
    estimate_price_change_pct,
    future_value_with_fees,
    interpolate_curve,
    macaulay_duration,
    modified_duration,
    price_from_yield,
    solve_yield,
    yield_to_call,
    yield_to_maturity,
)


# ---------------------------------------------------------------------------
# discount_factor / price_from_yield
# ---------------------------------------------------------------------------

def test_discount_factor_one_period():
    assert discount_factor(0.06, freq=2, n_periods=1) == pytest.approx(1 / 1.03)


def test_price_at_par_when_yield_equals_coupon():
    price = price_from_yield(face=1000, coupon_rate=0.05, yld=0.05, years_to_maturity=10)
    assert price == pytest.approx(1000, abs=1e-6)


def test_price_above_par_when_yield_below_coupon():
    price = price_from_yield(face=1000, coupon_rate=0.05, yld=0.03, years_to_maturity=10)
    assert price > 1000


def test_price_below_par_when_yield_above_coupon():
    price = price_from_yield(face=1000, coupon_rate=0.05, yld=0.08, years_to_maturity=10)
    assert price < 1000


def test_raising_yield_always_lowers_price():
    low_yield_price = price_from_yield(face=1000, coupon_rate=0.05, yld=0.04, years_to_maturity=10)
    high_yield_price = price_from_yield(face=1000, coupon_rate=0.05, yld=0.09, years_to_maturity=10)
    assert high_yield_price < low_yield_price


def test_zero_coupon_price_is_just_discounted_face():
    price = price_from_yield(face=1000, coupon_rate=0.0, yld=0.05, years_to_maturity=5)
    assert price == pytest.approx(1000 * discount_factor(0.05, 2, 10))


# ---------------------------------------------------------------------------
# yield_to_maturity / yield_to_call
# ---------------------------------------------------------------------------

def test_ytm_round_trips_price_from_yield():
    price = price_from_yield(face=1000, coupon_rate=0.05, yld=0.0725, years_to_maturity=15)
    recovered = yield_to_maturity(price, face=1000, coupon_rate=0.05, years_to_maturity=15)
    assert recovered == pytest.approx(0.0725, abs=1e-8)


def test_price_above_par_means_ytm_below_coupon():
    price = price_from_yield(face=1000, coupon_rate=0.06, yld=0.04, years_to_maturity=10)
    ytm = yield_to_maturity(price, face=1000, coupon_rate=0.06, years_to_maturity=10)
    assert ytm < 0.06


def test_price_below_par_means_ytm_above_coupon():
    price = price_from_yield(face=1000, coupon_rate=0.06, yld=0.09, years_to_maturity=10)
    ytm = yield_to_maturity(price, face=1000, coupon_rate=0.06, years_to_maturity=10)
    assert ytm > 0.06


def test_solve_yield_rejects_nonpositive_price():
    with pytest.raises(ValueError):
        solve_yield(price=0, face=1000, coupon_rate=0.05, years_to_maturity=10)


def test_ytm_handles_zero_yield():
    # At y=0 price is just the sum of undiscounted cash flows.
    price = 1000 + 10 * 0.05 * 1000  # face + 10 years of coupon, no discounting
    ytm = yield_to_maturity(price, face=1000, coupon_rate=0.05, years_to_maturity=10)
    assert ytm == pytest.approx(0.0, abs=1e-6)


def test_ytm_handles_negative_yield():
    price = price_from_yield(face=1000, coupon_rate=0.02, yld=-0.005, years_to_maturity=5)
    ytm = yield_to_maturity(price, face=1000, coupon_rate=0.02, years_to_maturity=5)
    assert ytm == pytest.approx(-0.005, abs=1e-8)


def test_yield_to_call_uses_call_price_and_call_date():
    price = price_from_yield(face=1000, coupon_rate=0.07, yld=0.05, years_to_maturity=5, redemption=1030)
    ytc = yield_to_call(price, face=1000, coupon_rate=0.07, years_to_call=5, call_price=1030)
    assert ytc == pytest.approx(0.05, abs=1e-8)


# ---------------------------------------------------------------------------
# current_yield
# ---------------------------------------------------------------------------

def test_current_yield_is_coupon_over_price():
    cy = current_yield(face=1000, coupon_rate=0.05, price=900)
    assert cy == pytest.approx(50 / 900)


# ---------------------------------------------------------------------------
# duration / convexity
# ---------------------------------------------------------------------------

def test_zero_coupon_macaulay_duration_equals_maturity():
    dur = macaulay_duration(face=1000, coupon_rate=0.0, yld=0.05, years_to_maturity=7)
    assert dur == pytest.approx(7.0, abs=1e-9)


def test_duration_falls_as_maturity_approaches():
    long_dur = macaulay_duration(face=1000, coupon_rate=0.05, yld=0.05, years_to_maturity=20)
    short_dur = macaulay_duration(face=1000, coupon_rate=0.05, yld=0.05, years_to_maturity=5)
    assert short_dur < long_dur


def test_higher_coupon_means_lower_duration_at_same_maturity():
    low_coupon_dur = macaulay_duration(face=1000, coupon_rate=0.02, yld=0.05, years_to_maturity=10)
    high_coupon_dur = macaulay_duration(face=1000, coupon_rate=0.08, yld=0.05, years_to_maturity=10)
    assert high_coupon_dur < low_coupon_dur


def test_modified_duration_is_macaulay_discounted_one_period():
    mac = macaulay_duration(face=1000, coupon_rate=0.05, yld=0.06, years_to_maturity=10)
    mod = modified_duration(mac, yld=0.06)
    assert mod == pytest.approx(mac / 1.03)


def test_duration_estimate_close_at_10bp_and_off_at_300bp():
    face, coupon_rate, yld, years = 1000, 0.05, 0.06, 20
    price = price_from_yield(face, coupon_rate, yld, years)
    mac = macaulay_duration(face, coupon_rate, yld, years)
    mod = modified_duration(mac, yld)
    cvx = convexity(face, coupon_rate, yld, years)

    for delta, tight in [(0.001, 1e-4), (0.03, 1e-4)]:
        estimate_pct = estimate_price_change_pct(mod, cvx, delta)
        actual_pct = price_from_yield(face, coupon_rate, yld + delta, years) / price - 1
        error = abs(estimate_pct - actual_pct)
        if delta == 0.001:
            small_move_error = error
        else:
            large_move_error = error

    # The duration+convexity estimate is far closer for a small move than a large one.
    assert small_move_error < large_move_error
    assert small_move_error < 1e-4


# ---------------------------------------------------------------------------
# accrued interest / day count / clean & dirty price
# ---------------------------------------------------------------------------

def test_day_count_actual_actual_halfway_through_period():
    frac = day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), date(2024, 7, 1), convention="actual/actual")
    assert frac == pytest.approx(91 / 182)


def test_day_count_30_360_exact_half_period():
    frac = day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), date(2024, 7, 1), convention="30/360")
    assert frac == pytest.approx(0.5)


def test_day_count_rejects_unknown_convention():
    with pytest.raises(ValueError):
        day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), date(2024, 7, 1), convention="actual/365")


def test_accrued_interest_and_clean_dirty_round_trip():
    accrued = accrued_interest(
        face=1000,
        coupon_rate=0.06,
        freq=2,
        prev_coupon=date(2024, 1, 1),
        settlement=date(2024, 4, 1),
        next_coupon=date(2024, 7, 1),
        convention="30/360",
    )
    assert accrued == pytest.approx(15.0)  # half of a $30 semiannual coupon
    dirty = dirty_price(clean=980.0, accrued=accrued)
    assert clean_price(dirty, accrued) == pytest.approx(980.0)


def test_accrued_interest_zero_at_settlement_on_coupon_date():
    accrued = accrued_interest(
        face=1000,
        coupon_rate=0.06,
        freq=2,
        prev_coupon=date(2024, 1, 1),
        settlement=date(2024, 1, 1),
        next_coupon=date(2024, 7, 1),
    )
    assert accrued == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# classify_curve
# ---------------------------------------------------------------------------

def test_classify_curve_normal():
    curve = pd.Series({1 / 12: 0.05, 3 / 12: 0.052, 2: 0.045, 10: 0.043, 30: 0.045})
    # bump 10y above 3mo to make it clearly normal
    curve[10] = 0.06
    assert classify_curve(curve) == "normal"


def test_classify_curve_inverted():
    curve = pd.Series({3 / 12: 0.055, 10: 0.04})
    assert classify_curve(curve) == "inverted"


def test_classify_curve_flat():
    curve = pd.Series({3 / 12: 0.05, 10: 0.052})
    assert classify_curve(curve) == "flat"


def test_classify_curve_requires_3mo_and_10y_points():
    curve = pd.Series({1: 0.05, 5: 0.05})
    with pytest.raises(ValueError):
        classify_curve(curve)


# ---------------------------------------------------------------------------
# interpolate_curve
# ---------------------------------------------------------------------------

def test_interpolate_curve_midpoint():
    curve = pd.Series({2: 0.04, 4: 0.05})
    assert interpolate_curve(curve, 3) == pytest.approx(0.045)


def test_interpolate_curve_flat_extrapolates_past_ends():
    curve = pd.Series({2: 0.04, 10: 0.05})
    assert interpolate_curve(curve, 30) == pytest.approx(0.05)
    assert interpolate_curve(curve, 0.5) == pytest.approx(0.04)


# ---------------------------------------------------------------------------
# future_value_with_fees
# ---------------------------------------------------------------------------

def test_future_value_zero_years_returns_starting_amount():
    assert future_value_with_fees(1000, 100, 0.07, 0.01, years=0) == 1000


def test_future_value_higher_fee_always_lower_ending_value():
    low = future_value_with_fees(10_000, 6_000, 0.07, 0.0003, years=30)
    high = future_value_with_fees(10_000, 6_000, 0.07, 0.0075, years=30)
    assert high < low


def test_future_value_matches_hand_computed_two_years():
    # year 1: 1000*1.05 + 100 = 1150; year 2: 1150*1.05 + 100 = 1307.5
    fv = future_value_with_fees(1000, 100, gross_return=0.06, expense_ratio=0.01, years=2)
    assert fv == pytest.approx(1307.5)


# ---------------------------------------------------------------------------
# call_breakeven_years
# ---------------------------------------------------------------------------

def test_call_breakeven_divides_premium_by_extra_income():
    years = call_breakeven_years(price_paid=1080, call_price=1020, extra_annual_coupon=15)
    assert years == pytest.approx(4.0)


def test_call_breakeven_none_when_no_premium_at_risk():
    assert call_breakeven_years(price_paid=1000, call_price=1020, extra_annual_coupon=15) is None


def test_call_breakeven_none_when_extra_income_nonpositive():
    assert call_breakeven_years(price_paid=1080, call_price=1020, extra_annual_coupon=0) is None
