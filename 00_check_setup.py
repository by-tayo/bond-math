"""Verify the environment is ready: bond math round-trips correctly (no
network needed), and the FRED API key works (needed for the curve scripts).
"""
import sys

from bond_common import get_fred_client, price_from_yield, yield_to_maturity


def main() -> int:
    price = price_from_yield(face=1000, coupon_rate=0.05, yld=0.06, years_to_maturity=10)
    recovered_yield = yield_to_maturity(price, face=1000, coupon_rate=0.05, years_to_maturity=10)
    if abs(recovered_yield - 0.06) > 1e-6:
        print(f"[FAIL] price/yield round trip is off: expected 0.06, got {recovered_yield:.8f}")
        return 1
    print(f"[OK] bond math round trip: price={price:.4f}, recovered yield={recovered_yield:.6f}")

    try:
        fred = get_fred_client()
    except RuntimeError as e:
        print(f"[FAIL] {e}")
        return 1

    try:
        s = fred.get_series("DGS10")
    except Exception as e:
        print(f"[FAIL] Could not reach FRED: {e}")
        return 1

    print(f"[OK] FRED API key works. DGS10 has {len(s)} observations, most recent: {s.index[-1].date()}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
