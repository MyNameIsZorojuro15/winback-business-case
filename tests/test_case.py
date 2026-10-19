"""The economics, the power calculation, and the workbook's formulas agree with each other."""
from __future__ import annotations

import math
from pathlib import Path

import formulas
import pytest

from winback.excel import build
from winback.model import (Inputs, breakeven_b, breakeven_c, load_inputs, minimum_detectable_uplift, power,
                           profit_b, profit_c, profit_none, required_n_per_arm)

I = Inputs(n=1000, p0=0.25, revenue_per_returner=500.0, top_value_customers=200, margin=0.40, discount=0.10)


def test_breakeven_is_where_profit_equals_doing_nothing():
    assert profit_b(I, breakeven_b(I)) == pytest.approx(profit_none(I))
    assert profit_c(I, breakeven_c(I)) == pytest.approx(profit_none(I))


def test_discount_needs_more_uplift_than_reminder():
    assert breakeven_b(I) - I.p0 > breakeven_c(I) - I.p0


def test_discount_at_or_above_margin_never_pays():
    assert math.isinf(breakeven_b(Inputs(1000, 0.25, 500.0, 200, margin=0.10, discount=0.10)))


def test_power_matches_textbook_sample_size():
    # Classic formula for p0 = 0.25 vs p1 = 0.30, alpha 0.05, power 0.8: about 1,250 per group.
    n = required_n_per_arm(0.25, 0.05)
    assert 1200 <= n <= 1300
    assert power(n, 0.25, 0.30) >= 0.80 > power(n - 25, 0.25, 0.30)


def test_minimum_detectable_uplift_is_consistent_with_power():
    mde = minimum_detectable_uplift(400, 0.25)
    assert power(400, 0.25, 0.25 + mde) == pytest.approx(0.80, abs=0.005)


def test_workbook_formulas_match_python(tmp_path):
    i = load_inputs()
    path = build(i, tmp_path / "case.xlsx")
    sol = formulas.ExcelModel().loads(str(path)).finish().calculate()

    def cell(sheet, ref):
        for k, v in sol.items():
            if k.upper().endswith(f"{sheet}'!{ref}"):
                return v.value[0][0]
        raise KeyError(ref)

    assert cell("OPTIONS", "C4") == pytest.approx(100 * (breakeven_b(i) - i.p0))
    assert cell("OPTIONS", "D4") == pytest.approx(100 * (breakeven_c(i) - i.p0))
    assert cell("OPTIONS", "D9") == pytest.approx(profit_c(i, i.p0 + 0.03) - profit_none(i))
    assert cell("SENSITIVITY", "E4") == pytest.approx(100 * (breakeven_b(i) - i.p0))
