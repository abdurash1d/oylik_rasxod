import math
from typing import List

from sqlalchemy.orm import Session

from app.schemas import Insight, InsightsResponse
from app.services.debts import list_debts
from app.services.expenses import monthly_summary
from app.services.settings import get_or_create_settings
from app.services.stats import month_totals, prev_month, savings_rate

# Display order: most urgent first.
_SEVERITY_ORDER = {"bad": 0, "warn": 1, "info": 2, "good": 3}

# Fixed thresholds (savings target and emergency months are user-configurable).
TOP_CATEGORY_PCT = 35
TREND_DELTA_PCT = 15
MAX_BUDGET_ALERTS = 3


def _savings_level(income: int, rate: int, target: int) -> str:
    if income <= 0:
        return "none"
    if rate >= target:
        return "good"
    if rate >= round(target / 2):
        return "ok"
    return "low"


def build_insights(db: Session, user_id: int, year: int, month: int) -> InsightsResponse:
    settings = get_or_create_settings(db, user_id)
    savings_target = settings.savings_target_pct
    emergency_months = settings.emergency_months
    budgets = settings.category_budgets or {}

    summary = monthly_summary(db, user_id, year, month)
    income = summary.income_total_uzs
    expense = summary.expense_total_uzs
    saved = summary.balance_uzs
    rate = savings_rate(income, expense)
    level = _savings_level(income, rate, savings_target)

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
        sev = "good" if rate >= savings_target else "info" if rate >= round(savings_target / 2) else "warn"
        insights.append(Insight(
            code="savings_rate", severity=sev,
            params={"pct": rate, "target": savings_target, "saved": saved},
        ))

    # Category budgets exceeded.
    budget_alerts = 0
    for cat in summary.by_category:
        limit = budgets.get(cat.category_key)
        if limit and cat.total_uzs > limit:
            insights.append(Insight(
                code="budget_over", severity="warn",
                params={
                    "category_key": cat.category_key,
                    "spent": cat.total_uzs,
                    "limit": int(limit),
                    "pct": round(cat.total_uzs / limit * 100),
                },
            ))
            budget_alerts += 1
            if budget_alerts >= MAX_BUDGET_ALERTS:
                break

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
        target = expense * emergency_months
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
    if income > 0 and expense <= income and rate >= savings_target \
            and not any(i.severity in ("bad", "warn") for i in insights):
        insights.append(Insight(code="doing_great", severity="good", params={"pct": rate}))

    insights.sort(key=lambda i: _SEVERITY_ORDER.get(i.severity, 9))

    return InsightsResponse(
        savings_rate_pct=rate, savings_level=level,
        income_total_uzs=income, expense_total_uzs=expense, saved_uzs=saved,
        insights=insights,
    )
