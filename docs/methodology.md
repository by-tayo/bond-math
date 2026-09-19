# Methodology

Every number this tool produces should be reproducible from this document
plus `bond_common.py`. If a number can't be traced back to something
stated here, that's a bug in this document, not a secret in the code.

## Compounding convention

Semiannual compounding (`freq=2`) is the default everywhere, because it's
the US convention for Treasury and corporate bonds — a "5% coupon" bond
pays 2.5% of face every six months, and yields are quoted as that
per-period rate doubled (the "bond-equivalent yield" convention), not as a
true annual effective rate. Every function that takes a yield or a
maturity takes `freq` as a parameter, so an annual-pay or quarterly-pay
bond is `freq=1` or `freq=4` — nothing in the code assumes 2 except the
default value.

## Day count conventions

Used only by `accrued_interest` / `day_count_fraction` (settlement between
coupon dates); the core pricing/yield/duration functions assume valuation
exactly on a coupon date and don't need a day count at all.

- **30/360** ("bond basis") — every month treated as exactly 30 days, every
  year as 360. Used for corporate and municipal bonds.
- **Actual/actual** — real calendar days in both the elapsed period and the
  full period. Used for Treasuries.

The convention is always an explicit parameter (`convention="30/360"` or
`"actual/actual"`), never a hard-coded default baked into a formula, because
using the wrong one for an instrument type is a real source of small
pricing errors, not a rounding curiosity.

## What yield-to-maturity assumes — and why it's optimistic

YTM is the single discount rate that makes the present value of a bond's
remaining cash flows equal its price. Solving for it (`solve_yield`,
bisection) implicitly assumes **every coupon is reinvested at that same
rate** until maturity. Real reinvestment rates move with the market, so:

- If rates fall after you buy, your realized return will be *below* the
  quoted YTM — coupons get reinvested at a lower rate than the one you
  locked in on the bond itself.
- If rates rise, realized return can exceed YTM.

YTM is the standard, quoted, comparable number — but it is a hypothetical,
not a promise. A bond's *actual* return over any holding period depends on
the path rates take, not just today's yield.

## What this tool ignores entirely

- **Credit risk.** Every price and yield here assumes the bond pays exactly
  what it promises, on time, in full. There's no default probability, no
  recovery rate, no credit spread model — a AAA bond and a distressed bond
  with the same coupon and maturity price identically here. Real corporate
  and municipal bond yields include a credit spread this tool doesn't
  compute or explain.
- **Option-adjusted spread (OAS) for callable bonds.** `yield_to_call`
  prices to *one* assumed call date and price, which is the standard
  simplification (and what "yield to worst" is built from — the minimum of
  YTM and YTC across all call dates) — but it isn't an option valuation. A
  proper treatment models the call as an embedded option the issuer holds,
  values it (typically with a short-rate model like Black-Karasinski or
  Hull-White), and backs out a spread net of that option's value. This tool
  doesn't do that; `07_call_breakeven.py` is a cash-flow approximation of
  "how long until the extra coupon pays for the call risk," not an option
  price.
- **Municipal bond tax treatment.** Muni coupon income is typically exempt
  from federal (and sometimes state) tax, which is the entire reason
  municipal yields are quoted lower than taxable equivalents. This tool has
  no tax-equivalent-yield calculation and no tax bracket input — a muni's
  after-tax advantage depends entirely on the investor's marginal rate, and
  isn't modeled here.
- **Zero-coupon phantom income.** A zero-coupon bond pays no cash before
  maturity, but in a US taxable account the IRS still taxes the *imputed*
  interest (original issue discount) every year as if it had been paid —
  "phantom income" you owe tax on without receiving cash to pay it. This
  tool prices zero-coupon bonds correctly but doesn't model or flag this
  tax treatment; it matters most in a taxable (non-retirement) account.

## Applications-layer simplifications

- **Rate shock table** (`04_rate_shock.py`) reprices with a parallel shift
  in yield — every point on the curve moves by the same number of basis
  points. Real curve moves aren't parallel (short rates and long rates
  often move by different amounts), so this shows sensitivity to *a*
  rate move, not a forecast of any specific one.
- **Ladder builder** (`05_ladder_builder.py`) assumes every rung is a
  newly-issued bond priced at par, with a coupon equal to today's
  interpolated Treasury yield at that maturity. It also assumes each rung
  reinvests, at maturity, at whatever the long end of *today's* curve
  happens to be — which is a placeholder for "the rate at that future
  date," not a forecast of it. A real ladder's reinvestment rate is
  unknown until it happens.
- **Fee drag calculator** (`06_fee_drag.py`) assumes a constant annual
  gross return and annual (not continuous or monthly) compounding and fee
  deduction — real markets don't return the same amount every year, and
  real fund fees accrue daily against NAV. The point of the calculator is
  the *shape* of fee drag over a long horizon, not a forecast of any
  specific fund's future balance.
- **Call breakeven** (`07_call_breakeven.py`) compares undiscounted cash
  coupon income to a capital-loss-at-call, with no time value of money in
  the breakeven calculation itself — it answers "how many years of extra
  coupon dollars," not "what's the NPV-neutral holding period." See the
  OAS note above for what a rigorous version would require.

## Reproducing a number

Every script prints or writes exactly what it computes, and every
computation is one or a few calls into `bond_common.py`. To check any
number by hand: find the script that produced it, read the inputs at the
top of that script (or the CLI/config values it used), and call the same
`bond_common` function yourself with those inputs.
