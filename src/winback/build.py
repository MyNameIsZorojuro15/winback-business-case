"""Rebuild every output from inputs/inputs.json: results.json, the Excel workbook and the deck.

Usage: python -m winback.build
"""
from __future__ import annotations

import json
from pathlib import Path

from winback.deck import build as build_deck
from winback.excel import build as build_workbook
from winback.model import ASSUMPTIONS, load_inputs, sensitivity_b, sensitivity_c, summary

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    i = load_inputs()
    results = {"summary": summary(i), "sensitivity_option_b_uplift_pp": sensitivity_b(i),
               "sensitivity_option_c_uplift_pp": sensitivity_c(i), "assumptions": ASSUMPTIONS,
               "history": json.loads((ROOT / "inputs" / "inputs.json").read_text(encoding="utf-8"))["history"]}
    (OUT / "results.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    build_workbook(i, OUT / "winback_business_case.xlsx")
    build_deck(i, ROOT / "inputs" / "inputs.json", OUT / "winback_recommendation.pdf")
    print(json.dumps(results["summary"], indent=1))


if __name__ == "__main__":
    main()
