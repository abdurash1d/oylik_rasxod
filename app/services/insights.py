import math
from typing import List

from sqlalchemy.orm import Session

from app.schemas import Insight, InsightsResponse
from app.services.debts import list_debts
from app.services.expenses import monthly_summary
from app.services.stats import month_totals, prev_month, savings_rate

# Display order: most urgent first.
_SEVERITY_ORDER = {"bad": 0, "warn": 1, "info": 2, "good": 3}

# Recommended ceilings used by the rules.
SAVINGS_TARGET_PCT = 20
TOP_CATEGORY_PCT = 35
TREND_DELTA_PCT = 15
EMERGENCY_FUND_MONTHS = 3


def _savings_level(income: int, rate: int) -> str:
    if income <= 0:
        return "none"
    if rate >= SAVINGS_TARGET_PCT:
        return "good"
    if rate >= 10:
        return "ok"
    return "low"


def build_insights(db: Session, user_id: int, year: int, month: int) -> InsightsResponse:
    summary = monthly_summary(db, user_id, year, month)
    income = summary.income_total_uzs
    expense = summary.expense_total_uzs
    saved = summary.balance_uzs
    rate = savings_rate(income, expense)
    level = _savings_level(income, rate)

    insights: List[Insight] = []

    # No activity yet.
    if income <= 0 and expense <= 0:
        insights.append(Insight(code="no_data", severity="info", params={}))
        return InsightsResponse(
            savings_rate_pct=rate, savings_level=level,
            income_total_uzs=income, expense_total_uzs=expense, saved_uzs=saved,
            insights=insights,
        )

    # Overspending.
    if income > 0 and expense > income:
        insights.append(Insight(code="overspend", severity="bad", params={"over": expense - income}))

    # Savings rate verdict.
    if income > 0:
        sev = "good" if rate >= SAVINGS_TARGET_PCT else "info" if rate >= 10 else "warn"
        insights.append(Insight(
            code="savings_rate", severity=sev,
            params={"pct": rate, "target": SAVINGS_TARGET_PCT, "saved": saved},
        ))

    # Concentrated spending in one category.
    if expense > 0 and summary.by_category:
        top = summary.by_category[0]  # already sorted desc
        pct = round(top.total_uzs / expense * 100)
        if pct >= TOP_CATEGORY_PCT:
            insights.append(Insight(
                code="top_category", severity="warn",
                params={"category_key": top.category_key, "pct": pct},
            ))

    # Spending trend vs previous month.
    py, pm = prev_month(year, month)
    _, prev_expense = month_totals(db, user_id, py, pm)
    if prev_expense > 0:
        delta = round((expense - prev_expense) / prev_expense * 100)
        if delta >= TREND_DELTA_PCT:
            insights.append(Insight(code="trend_up", severity="warn", params={"pct": abs(delta)}))
        elif delta <= -TREND_DELTA_PCT:
            insights.append(Insight(code="trend_down", severity="good", params={"pct": abs(delta)}))

    # Emergency fund guidance (safe, conservative target).
    if expense > 0:
        target = expense * EMERGENCY_FUND_MONTHS
        if saved > 0:
            insights.append(Insight(
                code="emergency_fund", severity="info",
                params={"target": target, "months": math.ceil(target / saved)},
            ))

    # Debt prioritisation.
    totals = list_debts(db, user_id).totals
    if totals.borrowed_outstanding > 0:
        insights.append(Insight(code="debt_owe", severity="warn", params={"amount": totals.borrowed_outstanding}))
    elif totals.lent_outstanding > 0:
        insights.append(Insight(code="debt_lent", severity="info", params={"amount": totals.lent_outstanding}))

    # Positive reinforcement when things look healthy.
    if income > 0 and expense <= income and rate >= SAVINGS_TARGET_PCT \
            and not any(i.severity in ("bad", "warn") for i in insights):
        insights.append(Insight(code="doing_great", severity="good", params={"pct": rate}))

    insights.sort(key=lambda i: _SEVERITY_ORDER.get(i.severity, 9))

    return InsightsResponse(
        savings_rate_pct=rate, savings_level=level,
        income_total_uzs=income, expense_total_uzs=expense, saved_uzs=saved,
        insights=insights,
    )
