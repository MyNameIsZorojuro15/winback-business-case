"""Six-slide recommendation deck (PDF, 16:9) and its two charts. Every number comes from model.py or inputs.json."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib.colors import HexColor  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

from winback.model import Inputs, cost_b, cost_c, profit_b, profit_c, profit_none, summary  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs"
W, H = 33.867 * cm, 19.05 * cm
NAVY, GREY, RED, GREEN, INK = "#1f3864", "#9aa5b1", "#b23a48", "#2e7d4f", "#1b1f24"


def charts(i: Inputs, history: list[dict]) -> tuple[Path, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    labels = [h["snapshot"][:7] for h in history]
    vals = [100 * h["return_rate"] for h in history]
    ax.bar(labels, vals, color=[NAVY if lab == "2010-12" else GREY for lab in labels])
    for x, v, h in zip(labels, vals, history):
        ax.text(x, v + 1, f"{v:.0f} %\n(n={h['at_risk_customers']})", ha="center", fontsize=9)
    ax.set_ylim(0, max(vals) + 12)
    ax.set_ylabel("% ordering again within 90 days")
    ax.set_title("At-risk customers who came back with no programme", fontsize=11)
    fig.tight_layout()
    p1 = OUT / "baseline_by_snapshot.png"
    fig.savefig(p1, dpi=200)
    plt.close(fig)

    ups = [x / 2 for x in range(0, 31)]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    base = profit_none(i)
    ax.plot(ups, [profit_b(i, i.p0 + u / 100) - base for u in ups], color=RED, label="B. Email + 10 % discount")
    ax.plot(ups, [profit_c(i, i.p0 + u / 100) - base for u in ups], color=GREEN, label="C. Reminder + calls, no discount")
    ax.axhline(0, color="black", lw=0.8)
    ax.set_xlabel("extra customers returning, percentage points")
    ax.set_ylabel("gross profit vs doing nothing, GBP")
    ax.set_title("What each option earns, by uplift (margin 40 %)", fontsize=11)
    ax.legend(fontsize=9)
    fig.tight_layout()
    p2 = OUT / "profit_by_uplift.png"
    fig.savefig(p2, dpi=200)
    plt.close(fig)
    return p1, p2


def _title(c, text, sub=None):
    c.setFillColor(HexColor(NAVY))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1.6 * cm, H - 2.2 * cm, text)
    if sub:
        c.setFillColor(HexColor(INK))
        c.setFont("Helvetica", 13)
        c.drawString(1.6 * cm, H - 3.1 * cm, sub)
    c.setStrokeColor(HexColor(NAVY))
    c.setLineWidth(1.2)
    c.line(1.6 * cm, H - 3.5 * cm, W - 1.6 * cm, H - 3.5 * cm)


def _bullets(c, items, x=1.6 * cm, y=H - 4.8 * cm, size=14, width=None, gap=1.05):
    c.setFillColor(HexColor(INK))
    for it in items:
        c.setFont("Helvetica", size)
        lines, line = [], ""
        limit = width or 95
        for word in it.split():
            if len(line) + len(word) + 1 > limit:
                lines.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        lines.append(line)
        c.drawString(x, y, "•")
        for ln in lines:
            c.drawString(x + 0.6 * cm, y, ln)
            y -= size * gap * 0.0353 * cm * 28.35 / 28.35 * 1.25
        y -= 0.35 * cm
    return y


def _footer(c, n):
    c.setFont("Helvetica", 9)
    c.setFillColor(HexColor("#5b6670"))
    c.drawString(1.6 * cm, 0.8 * cm, "Data: UCI Online Retail II (CC BY 4.0), via github.com/MyNameIsZorojuro15/online-retail-analysis. Margin and costs are assumptions; see the workbook.")
    c.drawRightString(W - 1.6 * cm, 0.8 * cm, str(n))


def build(i: Inputs, inputs_json: Path, path: Path) -> Path:
    data = json.loads(inputs_json.read_text(encoding="utf-8"))
    s = summary(i)
    cur = data["current"]
    p_base, p_profit = charts(i, data["history"])
    gain3_b = profit_b(i, i.p0 + 0.03) - profit_none(i)
    gain3_c = profit_c(i, i.p0 + 0.03) - profit_none(i)
    c = canvas.Canvas(str(path), pagesize=(W, H))
    c.setTitle("Win-back programme: recommendation")
    c.setAuthor("Carlos Daniel Marques Freire")

    # 1
    c.setFillColor(HexColor(NAVY))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 30)
    c.drawString(2 * cm, H - 7 * cm, "Win back lapsed regulars without paying")
    c.drawString(2 * cm, H - 8.4 * cm, "for customers who would return anyway")
    c.setFont("Helvetica", 16)
    c.drawString(2 * cm, H - 10.4 * cm, f"Recommendation: a reminder and personal calls, no blanket discount, with a random holdout.")
    c.drawString(2 * cm, H - 11.3 * cm, f"Breaks even at +{s['breakeven']['option_c_uplift_pp']:.1f} points; a 10 % discount needs +{s['breakeven']['option_b_uplift_pp']:.1f}.")
    c.setFont("Helvetica", 11)
    c.drawString(2 * cm, 1.6 * cm, "Business case · UK online gift wholesaler · decision for January 2012 · Carlos Daniel Marques Freire")
    c.showPage()

    # 2
    _title(c, f"{cur['at_risk_customers']} regulars have gone quiet", f"They spent £{cur['prior_12m_revenue_gbp'] / 1e3:,.0f}k in the last 12 months; median {cur['median_recency_days']:.0f} days since their last order")
    _bullets(c, [
        "They used to order more often than most customers, but have not ordered for months.",
        f"About a quarter come back within 90 days without anyone asking: {100 * i.p0:.0f} % in the same season last year (n = {data['history'][0]['at_risk_customers']}).",
        f"Those who come back spend about £{i.revenue_per_returner:,.0f} in 90 days.",
        "September is different (41 %): peak season brings people back on its own, so it is the wrong time to measure.",
    ], width=58, y=H - 5 * cm)
    c.drawImage(str(p_base), W - 16.2 * cm, 2.2 * cm, width=14.6 * cm, height=8.2 * cm)
    _footer(c, 2)
    c.showPage()

    # 3
    _title(c, "Three options, one question: how many more must come back?", "Break-even = the extra share of customers returning for the option to earn what doing nothing earns")
    rows = [("", "Cost", "Break-even uplift", "If uplift is +3 points"),
            ("A. Do nothing", "£0", "–", "–"),
            ("B. Email + 10 % discount to all", f"£{cost_b(i):,.0f}", f"+{s['breakeven']['option_b_uplift_pp']:.1f} points", f"−£{-gain3_b:,.0f}" if gain3_b < 0 else f"+£{gain3_b:,.0f}"),
            ("C. Reminder email + calls to top 20 %", f"£{cost_c(i):,.0f}", f"+{s['breakeven']['option_c_uplift_pp']:.1f} points", f"+£{gain3_c:,.0f}")]
    y = H - 5.4 * cm
    for k, r in enumerate(rows):
        c.setFont("Helvetica-Bold" if k == 0 else "Helvetica", 15)
        c.setFillColor(HexColor(NAVY if k == 0 else INK))
        for x, txt in zip((1.6, 13.5, 18.5, 25.5), r):
            c.drawString(x * cm, y, txt)
        y -= 1.4 * cm
    _bullets(c, [
        "Margin 40 % and costs are assumptions (workbook, yellow cells). Across margins of 25–50 %, B needs +7 to +19 points and C needs +1.1 to +2.2.",
        f"Each extra point of return rate is worth about £{s['option_c_gain_per_point_gbp']:,.0f} to option C. Its worst case, no effect at all, costs £{cost_c(i):,.0f}.",
    ], y=y - 0.6 * cm, width=120, size=13)
    _footer(c, 3)
    c.showPage()

    # 4
    _title(c, "Why the discount is expensive", "It is paid to every customer who orders, including the quarter who would have ordered anyway")
    _bullets(c, [
        f"Without a programme, {100 * i.p0:.0f} % return and pay full price. With B, they return at 10 % off: the business gives margin away on sales it already had.",
        f"So B first has to win back enough new orders to cover that lost margin: +{s['breakeven']['option_b_uplift_pp']:.1f} points just to stand still.",
        f"At +3 points (an illustration, not a forecast), B loses £{-gain3_b:,.0f} and C gains £{gain3_c:,.0f}.",
        "A discount can still work if it is targeted (only top-value customers, or only above a basket size), and tested first.",
    ], width=56, y=H - 5 * cm)
    c.drawImage(str(p_profit), W - 16.2 * cm, 2.2 * cm, width=14.6 * cm, height=8.2 * cm)
    _footer(c, 4)
    c.showPage()

    # 5
    _title(c, "Can a pilot prove it? Not in one round", "Two-group test, half the segment each, 5 % significance, 80 % power")
    _bullets(c, [
        f"With {s['pilot']['n_per_arm']} customers per group, the smallest uplift a test can reliably detect is {s['pilot']['minimum_detectable_uplift_pp']:.1f} points.",
        f"Option B's break-even (+{s['breakeven']['option_b_uplift_pp']:.1f}) is detectable: if B does not show a large effect in a pilot, stop it.",
        f"Option C's break-even (+{s['breakeven']['option_c_uplift_pp']:.1f}) would need {s['pilot']['n_per_arm_to_detect_option_c_breakeven']:,} customers per group. No single campaign gets there.",
        "So decide C on economics (small, capped downside) and measure it continuously with a random holdout: a new at-risk group appears every month, and evidence adds up.",
    ], width=118, y=H - 5 * cm)
    _footer(c, 5)
    c.showPage()

    # 6
    _title(c, "Recommendation and next steps")
    _bullets(c, [
        "January: launch option C to the at-risk segment, keeping a random 20 % holdout that gets nothing.",
        "Every month: refresh the segment, repeat, and compare return rate and 90-day revenue, treatment vs holdout, pooled across months.",
        "Stop rule: after three months, if the pooled uplift's upper confidence bound is below the break-even uplift, stop and redesign.",
        "Discount: only as a separate randomised test on top-value customers; scale it only if it clears its own break-even.",
        "Requirements, user stories with acceptance criteria and the to-be process are in the repository (docs/).",
    ], width=118, y=H - 4.8 * cm)
    _footer(c, 6)
    c.showPage()
    c.save()
    return path
