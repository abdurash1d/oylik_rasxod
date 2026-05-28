# Design: "Spent vs. Saved" Dashboard Redesign

- **Date:** 2026-05-27
- **Status:** Approved (design); pending implementation plan
- **Branch:** `feature/spent-vs-saved-dashboard`
- **Component:** Telegram mini-app frontend (`rasxot_bot`)

## Context

`rasxot_bot` is a single-user Telegram mini-app for tracking monthly expenses and
income (currency: UZS). The owner requested two things:

1. **Per-category spending clarity** — for each category, clearly show how much was
   spent ("категорияга қанча пул сарфланганини кўрсатадиган қилиш").
2. **Spent vs. saved overview** — show how much money is spent and how much is set
   aside / left over ("қанча пул ишлатвоссан ва қанча пули олиб қўйвоссан").

Alongside this, give the dashboard a genuine visual cleanup ("increase the design and
functions").

The current dashboard already has a basic category breakdown list and a Chart.js pie,
three KPI cards (Доход / Расход / Остаток), add forms, and an inline-editable ledger,
but the layout is flat and the "how much did I save" story is not front-and-center.

## Goals

- Make "how much I spent vs. how much I kept this month" the focal point of the screen.
- Show each expense category with its amount, share %, and a ranked visual bar.
- Visually modernize the whole mini-app (header, forms, history) consistently.
- Normalize all UI text to consistent Russian.

## Non-Goals (tracked for later, NOT in this round)

- Telegram `initData` HMAC auth fix (known security gap — separate work).
- Alembic migrations.
- Budgets / per-category limits.
- Multi-currency.
- Tap-to-drill-down into a category's individual transactions.
- New analytics (trend chart, month-over-month).

## Decisions (from design interview)

| Decision | Choice |
|---|---|
| Meaning of "savings" | **Leftover** = income − spending for the month, computed automatically. No new entry type. |
| Scope | Focused: the new feature + a dashboard visual polish. |
| Category row content | Amount + share % + ranked horizontal bar (biggest first). |
| UI language | Russian, made consistent (translate the few Uzbek-only strings). |
| Layout direction | **Concept C** — a ring showing spent vs. set aside, with category bars below. |

## Architecture

This is **almost entirely a frontend change**. The existing API endpoint
`GET /api/summary/month` already returns the monthly income total, expense total,
balance, and per-category breakdown. Therefore:

- "Отложено" (saved) = the existing balance (income − expense). No new backend math.
- Category share % = `category_amount / total_expense * 100`, **computed on the frontend**
  from data the API already returns (zero backend risk, no migration concerns).

**No database or schema changes.** No Alembic work required.

### Files affected

- `app/templates/index.html` — rebuilt to the Concept C structure.
- `app/static/styles.css` — restyled for the new components (ring, bars, segmented
  toggle, polished forms and history rows).
- `app/api/routes.py` / `app/services/expenses.py` — **untouched** (percentages computed
  client-side). If a later decision moves % server-side, it would add a field to the
  summary response, but that is out of scope here.

## Layout (Concept C, top to bottom)

1. **Month header** — shows the selected month (e.g. `Май 2026`) with a control to
   change the viewed month, preserving the existing year/month selection behavior. No
   settings menu in this round (the ⚙️ in the mockup is decorative, not built).
2. **Spent/saved ring** — a CSS `conic-gradient` donut. Red arc = share of income spent,
   green arc = share saved. Center shows `ПОТРАЧЕНО / <amount> / N% дохода`.
3. **Legend line** under the ring: `🟢 Отложено <amount>` and `Доход <amount>`.
4. **Category bars** — section `РАСХОДЫ ПО КАТЕГОРИЯМ`: each row shows category name,
   `amount · %`, and a colored bar, ranked biggest-first. Each category has a stable color.
5. **Add section** — a segmented `Расход / Доход` toggle that swaps between the expense
   and income forms (category/type dropdown, amount, date, Сохранить).
6. **History** — the month's entries, newest first, each with edit/delete affordances
   (preserving the existing inline-edit capability).

The **Chart.js pie and its CDN `<script>` are removed** — the ring + bars replace it,
making the app lighter with no external dependency.

### Number & currency formatting

- Thousands separated by spaces, Russian style: `5 200 000`.
- Currency suffix `сум` where a value stands alone.

## Ring behavior & edge cases

| Situation | Ring & numbers |
|---|---|
| Income > spending (normal) | Red arc = % of income spent; green arc = saved. Center: `Потрачено X · N% дохода`. Legend: `🟢 Отложено Y`. |
| Overspend (spending > income) | Ring fully red. Legend shows `🔴 Перерасход −Z` in red instead of "Отложено". |
| No income logged (income = 0) | Hide `% дохода` and the green arc; show `Потрачено X` + hint `Доход не указан`. |
| Empty month (no expenses or income) | Friendly empty state: `Нет данных за <месяц>. Добавьте первый расход.` |

## Testing / Verification

- Existing Python tests remain valid (the API surface is unchanged).
- Manually verify the four dashboard states render correctly: normal, overspend,
  no-income, and empty month.
- Verify category bars rank correctly and percentages sum sensibly (~100%).
- Verify add (expense + income), edit, and delete still work end-to-end against the
  unchanged API.
- Confirm the mini-app renders well at narrow (phone) widths inside Telegram.

## Open Questions

None outstanding. Owner approved the design and delegated detail decisions
("just go, you know what is good").
