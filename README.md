# Win-back programme: business case, requirements and measurement plan

A business-analysis case built on real data: should a UK online gift wholesaler try to win back
customers who used to order often and have gone quiet, and how?

**Recommendation:** send a reminder and call the top-value customers, **without a blanket discount**,
and keep a random 20 % holdout to measure it. It breaks even if 1.3 percentage points more customers
come back; a 10 % discount to everyone would need 9.7 points just to stand still.

| Deliverable | File |
|---|---|
| Recommendation deck (6 slides) | [`outputs/winback_recommendation.pdf`](outputs/winback_recommendation.pdf) |
| Business-case workbook with live formulas and sensitivity tables | [`outputs/winback_business_case.xlsx`](outputs/winback_business_case.xlsx) |
| Requirements: RACI, as-is and to-be process, MoSCoW, user stories with acceptance criteria, traceability, risks | [`docs/requirements.md`](docs/requirements.md) |
| All numbers | [`outputs/results.json`](outputs/results.json) |

## The situation (measured)

From the cleaned transactions in [online-retail-analysis](https://github.com/MyNameIsZorojuro15/online-retail-analysis)
(UCI Online Retail II, CC BY 4.0):

- **736 customers** are "at risk" on 1 December 2011: they used to order more often than most, but
  have not ordered for a median of 142 days. They spent **£812k** in the previous 12 months.
- **About a quarter come back on their own.** Applying the same rule at earlier dates and watching the
  next 90 days, with no programme:

| Segment date | At-risk customers | Ordered again within 90 days | Revenue per returning customer |
|---|---:|---:|---:|
| 1 Dec 2010 (same season) | 815 | 27.2 % | £562 |
| 1 Mar 2011 | 725 | 29.1 % | £618 |
| 1 Jun 2011 | 700 | 22.0 % | £510 |
| 1 Sep 2011 (peak season) | 659 | 41.4 % | £610 |

That baseline is the key fact. Any programme gets credit only for customers *beyond* those who would
have returned anyway.

## The options

| Option | Cost | Uplift needed to break even | Gain if uplift is +3 points |
|---|---:|---:|---:|
| A. Do nothing | £0 | – | – |
| B. Email + 10 % discount to all | £750 | **+9.7 points** | −£8,300 |
| C. Reminder email + calls to the top 20 % | £2,220 | **+1.3 points** | +£2,747 |

Assumptions (yellow cells in the workbook): gross margin 40 %, 3 analyst days at £250, 20-minute calls
at £30 an hour. Margin is not in the data, so it is tested from 25 % to 50 %: option B then needs +7.3
to +19.4 points, option C +1.1 to +2.2. Each extra point is worth about £1,656 to option C; its worst
case, no effect at all, costs £2,220.

**Why the discount is expensive:** it goes to everyone who orders, including the 27 % who would have
ordered anyway at full price. B has to win back enough extra orders to cover that before it earns
anything.

## Can a pilot prove it?

With the segment split in half (368 per group), 5 % significance and 80 % power, a test can only
detect an uplift of **9.6 points** or more. That is enough to test option B's break-even, so a discount
should only go ahead after a pilot shows a large effect. Option C's break-even (+1.3 points) would need
**17,569 customers per group**: no single campaign can prove it. So C is decided on its economics
(small, capped downside) and measured continuously with a random holdout, pooling each month's new
at-risk group, with a stop rule after three months.

## Method

| Step | File |
|---|---|
| Extract the baseline and the current segment from the retail data | [`scripts/extract_inputs.py`](scripts/extract_inputs.py) → [`inputs/inputs.json`](inputs/inputs.json) |
| Economics, break-even, sensitivity, power and sample size | [`src/winback/model.py`](src/winback/model.py) |
| Workbook with formulas | [`src/winback/excel.py`](src/winback/excel.py) |
| Deck and charts | [`src/winback/deck.py`](src/winback/deck.py) |
| Rebuild everything | `python -m winback.build` |
| Tests: break-even really is break-even, sample size matches the textbook, the workbook's formulas recalculate to the same numbers as the Python model | [`tests/`](tests/) |

Choices worth defending:

- **Baseline from the same season** (December), because September's 41 % shows how much the season
  alone moves return rates.
- **Break-even instead of a guessed uplift.** The data cannot say how many customers a reminder will
  bring back; it can say how many it must bring back to pay.
- **Segment scores use `CEIL(5 * CUME_DIST())`**, so customers with equal order counts get equal scores.
  Building this case exposed that the first version of the retail analysis used `NTILE`, which splits
  ties arbitrarily; that project was corrected.
- **The workbook is checked by recalculating it** with the `formulas` engine in the tests, so the Excel
  numbers cannot drift from the model.

## Limits

- Margin and costs are assumptions, shown as ranges, not facts from the data.
- The data ends in December 2011, so the programme is a decision on that date, not a live system.
- 13.4 % of revenue has no customer id and cannot be targeted or measured.
- The pilot figures use a normal approximation; the workbook uses the textbook closed form, the model
  solves exactly, and the two differ slightly (9.2 vs 9.6 points).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
python -m winback.build     # results.json, workbook, deck, from inputs/inputs.json
python -m pytest -q         # 6 tests
# optional: re-extract inputs (needs online-retail-analysis built next to this folder)
python scripts/extract_inputs.py
```

Designed and reviewed by me, written with an AI coding assistant (Claude Code); every number traces to
`outputs/results.json` and `inputs/inputs.json`.
