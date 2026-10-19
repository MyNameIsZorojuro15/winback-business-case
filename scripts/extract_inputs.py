"""Extract the case inputs from the cleaned sales table of online-retail-analysis and save them to inputs/.

The outputs are committed, so the business case can be rebuilt without re-running that project.
Usage: python scripts/extract_inputs.py [path/to/retail.duckdb]
Default path: ../online-retail-analysis/data/retail.duckdb

Segments use the same RFM rules as online-retail-analysis (sql/analysis/08_rfm_segments.sql):
12 months of history up to the snapshot, recency and frequency quintiles.
Two historical snapshots measure what at-risk customers did in the next 90 days with no programme;
the current snapshot (2011-12-01) gives the customers the programme would target.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT.parent / "online-retail-analysis" / "data" / "retail.duckdb"

SEGMENTS = """
WITH win AS (
    SELECT * FROM sales
    WHERE customer_id IS NOT NULL AND invoice_date >= TIMESTAMP '{snap}' - INTERVAL 12 MONTH AND invoice_date < TIMESTAMP '{snap}'
),
base AS (
    SELECT customer_id, datediff('day', max(invoice_date), TIMESTAMP '{snap}') AS recency_days,
           count(DISTINCT invoice) AS frequency, sum(revenue) AS monetary
    FROM win GROUP BY customer_id
),
scored AS (SELECT *, ceil(5 * cume_dist() OVER (ORDER BY recency_days DESC)) AS r,
                     ceil(5 * cume_dist() OVER (ORDER BY frequency)) AS f FROM base),
seg AS (
    SELECT *, CASE WHEN r >= 4 AND f >= 4 THEN 'champions' WHEN r >= 3 AND f >= 3 THEN 'loyal'
                   WHEN r >= 4 AND f <= 2 THEN 'recent_low' WHEN r <= 2 AND f >= 3 THEN 'at_risk'
                   WHEN r = 3 THEN 'need_attention' ELSE 'lapsed' END AS segment
    FROM scored
)
SELECT * FROM seg WHERE segment = 'at_risk'
"""

OUTCOME = """
SELECT a.customer_id, a.monetary AS prior_12m_gbp,
       coalesce(o.orders, 0) AS orders_90d, coalesce(o.revenue, 0) AS revenue_90d
FROM ({segments}) AS a
LEFT JOIN (
    SELECT customer_id, count(DISTINCT invoice) AS orders, sum(revenue) AS revenue
    FROM sales
    WHERE customer_id IS NOT NULL AND invoice_date >= TIMESTAMP '{snap}' AND invoice_date < TIMESTAMP '{snap}' + INTERVAL 90 DAY
    GROUP BY customer_id
) AS o USING (customer_id)
"""


def main() -> None:
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    con = duckdb.connect(str(db), read_only=True)
    history = []
    for snap in ["2010-12-01", "2011-03-01", "2011-06-01", "2011-09-01"]:
        if snap > "2011-09-10":
            break
        df = con.execute(OUTCOME.format(segments=SEGMENTS.format(snap=snap), snap=snap)).df()
        back = df[df.orders_90d > 0]
        history.append({"snapshot": snap, "at_risk_customers": int(len(df)), "returned_90d": int(len(back)),
                        "return_rate": round(len(back) / len(df), 4),
                        "revenue_per_returner_90d_gbp": round(float(back.revenue_90d.mean()), 2),
                        "median_prior_12m_gbp": round(float(df.prior_12m_gbp.median()), 2)})
    current = con.execute(SEGMENTS.format(snap="2011-12-01")).df().sort_values("monetary", ascending=False)
    top_n = int(round(0.2 * len(current)))
    out = {
        "source": "online-retail-analysis, cleaned sales table (UCI Online Retail II, CC BY 4.0)",
        "segment_rule": "RFM scores CEIL(5 * CUME_DIST()) on 12 months before the snapshot; at_risk = recency score <= 2 and frequency score >= 3",
        "history": history,
        "current": {"snapshot": "2011-12-01", "at_risk_customers": int(len(current)),
                    "prior_12m_revenue_gbp": round(float(current.monetary.sum()), 2),
                    "median_recency_days": float(current.recency_days.median()),
                    "top20_customers": top_n, "top20_prior_12m_revenue_gbp": round(float(current.monetary.head(top_n).sum()), 2)},
    }
    (ROOT / "inputs" / "inputs.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
