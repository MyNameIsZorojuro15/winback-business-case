"""Economics of the win-back options and the statistics of a pilot.

Notation (per 90-day campaign window):
  N   at-risk customers targeted                       (measured: inputs.json, current)
  p0  share who order again within 90 days unprompted  (measured: same-season historical snapshot)
  p1  share who order again with the programme         (unknown: the thing to find out)
  R   90-day revenue per returning customer, GBP       (measured: same snapshot)
  m   gross margin on revenue                          (ASSUMPTION; not in the data, so shown as a range)
  d   discount given to every customer who orders      (option B only)
  F   fixed cost of the option, GBP                    (ASSUMPTION, itemised in ASSUMPTIONS)

Gross profit from the group:
  no programme    N * p0 * R * m
  option B        N * p1 * R * (m - d) - F     the discount also goes to customers who would have ordered anyway
  option C        N * p1 * R * m - F           a reminder and calls, no discount

Break-even p1 is where an option's profit equals the no-programme profit.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]

ASSUMPTIONS = {
    "gross_margin": {"value": 0.40, "range": [0.25, 0.50], "basis": "Not in the data. Typical of a gift wholesaler; tested from 25 % to 50 %."},
    "discount": {"value": 0.10, "range": [0.05, 0.15], "basis": "Option B design choice."},
    "setup_days": {"value": 3, "basis": "Segment refresh, email build, tracking: 3 analyst days."},
    "day_rate_gbp": {"value": 250, "basis": "Loaded cost of an analyst day; assumption."},
    "call_minutes": {"value": 20, "basis": "Per call to a top-value customer, including notes."},
    "call_rate_gbp_per_hour": {"value": 30, "basis": "Loaded cost of an account manager hour; assumption."},
}


@dataclass(frozen=True)
class Inputs:
    n: int
    p0: float
    revenue_per_returner: float
    top_value_customers: int
    margin: float = ASSUMPTIONS["gross_margin"]["value"]
    discount: float = ASSUMPTIONS["discount"]["value"]

    @property
    def setup_cost(self) -> float:
        return ASSUMPTIONS["setup_days"]["value"] * ASSUMPTIONS["day_rate_gbp"]["value"]

    @property
    def call_cost(self) -> float:
        return self.top_value_customers * ASSUMPTIONS["call_minutes"]["value"] / 60 * ASSUMPTIONS["call_rate_gbp_per_hour"]["value"]


def load_inputs(path: Path = ROOT / "inputs" / "inputs.json", snapshot: str = "2010-12-01") -> Inputs:
    """Baseline from the historical snapshot in the same season as the launch (December)."""
    data = json.loads(path.read_text(encoding="utf-8"))
    hist = {h["snapshot"]: h for h in data["history"]}[snapshot]
    cur = data["current"]
    return Inputs(n=cur["at_risk_customers"], p0=hist["return_rate"], revenue_per_returner=hist["revenue_per_returner_90d_gbp"],
                  top_value_customers=cur["top20_customers"])


def profit_none(i: Inputs) -> float:
    return i.n * i.p0 * i.revenue_per_returner * i.margin


def cost_b(i: Inputs) -> float:
    return i.setup_cost


def cost_c(i: Inputs) -> float:
    return i.setup_cost + i.call_cost


def profit_b(i: Inputs, p1: float) -> float:
    return i.n * p1 * i.revenue_per_returner * (i.margin - i.discount) - cost_b(i)


def profit_c(i: Inputs, p1: float) -> float:
    return i.n * p1 * i.revenue_per_returner * i.margin - cost_c(i)


def breakeven_b(i: Inputs) -> float:
    """p1 at which option B earns the same as doing nothing."""
    if i.margin <= i.discount:
        return math.inf
    return (i.p0 * i.margin + cost_b(i) / (i.n * i.revenue_per_returner)) / (i.margin - i.discount)


def breakeven_c(i: Inputs) -> float:
    return i.p0 + cost_c(i) / (i.n * i.revenue_per_returner * i.margin)


def gain_per_point(i: Inputs) -> float:
    """Extra gross profit from option C for each percentage point of uplift."""
    return i.n * 0.01 * i.revenue_per_returner * i.margin


def power(n_per_arm: int, p0: float, p1: float, alpha: float = 0.05) -> float:
    """Power of a two-sided two-proportion z-test with equal arms (normal approximation)."""
    se0 = math.sqrt(2 * ((p0 + p1) / 2) * (1 - (p0 + p1) / 2) / n_per_arm)
    se1 = math.sqrt(p0 * (1 - p0) / n_per_arm + p1 * (1 - p1) / n_per_arm)
    z = norm.ppf(1 - alpha / 2)
    return float(norm.cdf((abs(p1 - p0) - z * se0) / se1))


def minimum_detectable_uplift(n_per_arm: int, p0: float, target_power: float = 0.80, alpha: float = 0.05) -> float:
    """Smallest uplift (p1 - p0) detected with the target power; bisection on power()."""
    lo, hi = 0.0, 1 - p0
    for _ in range(80):
        mid = (lo + hi) / 2
        if power(n_per_arm, p0, p0 + mid, alpha) < target_power:
            lo = mid
        else:
            hi = mid
    return hi


def required_n_per_arm(p0: float, uplift: float, target_power: float = 0.80, alpha: float = 0.05) -> int:
    n = 10
    while power(n, p0, p0 + uplift, alpha) < target_power:
        n = int(n * 1.1) + 1
    lo, hi = n // 1.1, n
    lo = int(lo)
    while lo < hi:
        mid = (lo + hi) // 2
        if power(mid, p0, p0 + uplift, alpha) < target_power:
            lo = mid + 1
        else:
            hi = mid
    return hi


def summary(i: Inputs) -> dict:
    half = i.n // 2
    be_b, be_c = breakeven_b(i), breakeven_c(i)
    return {
        "inputs": {"n": i.n, "p0": i.p0, "revenue_per_returner_gbp": i.revenue_per_returner, "top_value_customers": i.top_value_customers,
                   "margin": i.margin, "discount": i.discount},
        "costs_gbp": {"option_b": round(cost_b(i), 2), "option_c": round(cost_c(i), 2), "setup": i.setup_cost, "calls": round(i.call_cost, 2)},
        "baseline_gross_profit_gbp": round(profit_none(i), 2),
        "breakeven": {
            "option_b_p1": round(be_b, 4), "option_b_uplift_pp": round(100 * (be_b - i.p0), 2),
            "option_c_p1": round(be_c, 4), "option_c_uplift_pp": round(100 * (be_c - i.p0), 2),
        },
        "option_c_gain_per_point_gbp": round(gain_per_point(i), 2),
        "option_c_worst_case_gbp": round(-cost_c(i), 2),
        "pilot": {
            "n_per_arm": half,
            "minimum_detectable_uplift_pp": round(100 * minimum_detectable_uplift(half, i.p0), 2),
            "n_per_arm_to_detect_option_c_breakeven": required_n_per_arm(i.p0, be_c - i.p0),
            "n_per_arm_to_detect_option_b_breakeven": required_n_per_arm(i.p0, be_b - i.p0),
        },
    }


def sensitivity_b(i: Inputs, margins=(0.25, 0.30, 0.35, 0.40, 0.45, 0.50), discounts=(0.05, 0.10, 0.15)) -> list[dict]:
    rows = []
    for d in discounts:
        row = {"discount": d}
        for m in margins:
            j = Inputs(i.n, i.p0, i.revenue_per_returner, i.top_value_customers, margin=m, discount=d)
            be = breakeven_b(j)
            row[f"m{int(m * 100)}"] = round(100 * (be - i.p0), 1) if math.isfinite(be) else None
        rows.append(row)
    return rows


def sensitivity_c(i: Inputs, margins=(0.25, 0.30, 0.35, 0.40, 0.45, 0.50)) -> list[dict]:
    rows = []
    for m in margins:
        j = Inputs(i.n, i.p0, i.revenue_per_returner, i.top_value_customers, margin=m)
        rows.append({"margin": m, "breakeven_uplift_pp": round(100 * (breakeven_c(j) - i.p0), 2)})
    return rows
