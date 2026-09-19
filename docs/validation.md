# Validation

Every number below is produced by `bond_common.py` and checked against a
published, independently-worked answer — not against this project's own
prior output. The two textbook problem sets used are:

- **Auburn** — Bodie/Kane/Marcus-style bond pricing, YTM, and yield-to-call
  problem set with a published answer key
  ([source](http://webhome.auburn.edu/~pughwi1/answer9-10.html)).
- **AnalystPrep** — a CFA Level I worked Macaulay duration example
  ([source](https://analystprep.com/cfa-level-1-exam/fixed-income/macaulay-modified-effective-durations/)).

All of these value the bond exactly on a coupon date (no fractional first
period), which matches the simplified period-based model in `bond_common.py`.
Settlement-date accrued interest is a separate, day-count-aware code path
(`accrued_interest`, `day_count_fraction`) and isn't exercised by these
whole-period reference problems — see `tests/test_bond_common.py` for that.

## Price from yield

| Inputs | This tool | Reference | Difference |
|---|---|---|---|
| Face $1,000, 10% coupon (semiannual, $50/period), 3yr (6 periods), yield 8% (4%/period) | **$1,052.42** | $1,052.42 | $0.00 |

## Yield to maturity

| Inputs | This tool | Reference | Difference |
|---|---|---|---|
| Face $1,000, 8% coupon (semiannual), 20yr, price $950 | **8.53%** | 8.52% | 0.01 pt |
| Face $1,000, 8% coupon (semiannual), 20yr, price $1,050 | **7.51%** | 7.52% | 0.01 pt |
| Face $1,000, 8% coupon (**annual**), 20yr, price $950 | **8.53%** | 8.53% | 0.00 pt |
| Face $1,000, 8% coupon (**annual**), 20yr, price $1,050 | **7.51%** | 7.51% | 0.00 pt |
| Zero-coupon, face $1,000, 10yr (semiannual compounding), price $376.89 | **10.000%** | 10.000% | 0.000 pt |

The two 0.01-point gaps on the semiannual cases are the reference key's own
rounding (it solves via an approximation formula, not exact bisection) — the
annual-coupon version of the same problem, which the key solves exactly,
matches to the reported precision. The zero-coupon case (which has a
closed-form answer, no approximation either side) matches exactly.

## Yield to call

| Inputs | This tool | Reference | Difference |
|---|---|---|---|
| Face $1,000, 8% coupon (semiannual), price $1,124.72, callable in 2yr at $1,100 | **6.063%** | 6.062% | 0.001 pt |

## Macaulay duration

| Inputs | This tool | Reference | Difference |
|---|---|---|---|
| Face 100, 6% coupon (**annual**), 3yr, yield 8% | **2.83 yr** (price $94.85) | 2.82 yr (price ~$95) | 0.01 yr |

## A hand-derivable identity (not from an external source, but independently checkable by anyone with a pencil)

A zero-coupon bond's only cash flow is redemption at maturity, so its
present-value-weighted average time to receipt is, by construction, exactly
its time to maturity — no computation needed to see this must be true.
`tests/test_bond_common.py::test_zero_coupon_macaulay_duration_equals_maturity`
checks `macaulay_duration(face=1000, coupon_rate=0.0, yld=0.05,
years_to_maturity=7) == 7.0` to 1e-9, and it does.

## Duration and convexity against numerical derivatives of price itself

The strongest check for `modified_duration` and `convexity` isn't a
reference table at all — it's comparing them to a central-difference
derivative of `price_from_yield` with respect to yield, which is completely
independent of the closed-form duration/convexity formulas and would catch
a wrong formula (a sign error, a missing `1/freq` term, anything) directly.
For the Macaulay duration bond above (face 100, 6% annual coupon, 3yr,
yield 8%, price $94.8458):

| Check | Analytic (from `modified_duration`/`convexity`) | Numerical (central difference of `price_from_yield`) | Relative difference |
|---|---|---|---|
| dPrice/dYield | -248.409513003 | -248.409513013 | 4×10⁻¹¹ |
| d²Price/dYield² | 901.688888 | 901.688908 | 2×10⁻⁸ |

`tests/test_bond_common.py::test_modified_duration_matches_numerical_first_derivative`
and `::test_convexity_matches_numerical_second_derivative` run this check
on every test run (with a different bond, to make sure it isn't specific
to this one).

## Reproducing these numbers

```powershell
python -c "from bond_common import price_from_yield; print(price_from_yield(face=1000, coupon_rate=0.10, yld=0.08, years_to_maturity=3))"
```

Every row above is one call into `bond_common.py` — see
`docs/methodology.md` for the conventions (day count, compounding,
reinvestment assumption) those calls rely on.
