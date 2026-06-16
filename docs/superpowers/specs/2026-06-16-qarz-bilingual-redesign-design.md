# Qarz (Debts) + Bilingual + Dashboard Redesign — Design

**Date:** 2026-06-16
**Status:** Approved (design phase)
**Branch (base):** `feature/spent-vs-saved-dashboard`

## Summary

Extend the single-user "Oylik Rasxot Bot" Telegram mini-app with four cohesive
improvements, all within the existing Python/FastAPI + vanilla-JS + PostgreSQL
stack and the 480px mobile container:

1. **Qarzlar (debts)** — track money lent and borrowed, per person, with
   repayment history and live outstanding balances.
2. **Full RU/UZ bilingual UI** — a language toggle that switches every string
   without a page reload.
3. **Dashboard UI/UX redesign** — refined, tab-organized layout.
4. **Logic & performance pass** — parallelized fetches, cached static JS,
   targeted indexes.

These are additive: existing expense/income behavior is preserved.

## Non-goals

- Multi-user / sharing. App remains single-owner (`OWNER_TELEGRAM_ID`).
- Multi-currency. Amounts stay integer UZS.
- Interest, due-date reminders, or notifications on debts.
- Recurring transactions, budgets/targets, transfers between accounts.

## Concept decisions (locked)

- **Qarz is separate from spent-vs-saved.** Lending is not an expense;
  borrowing is not income. The ring is untouched by debts.
- **Qarz is all-time / current-state.** The Qarzlar view ignores the month
  picker — an outstanding debt is a current fact, not a monthly one.
- **Per-person, per-debt with repayment history.** Each debt is its own record;
  partial repayments accumulate against it; settled when outstanding = 0.
- **Bilingual is full-app**, not just the new feature. Toggle persisted locally.

## Architecture & file changes

### Backend (Python / FastAPI)

- **Models** (`app/models/`):
  - `debt.py` — `Debt`
  - `debt_repayment.py` — `DebtRepayment`
- **Service** (`app/services/debts.py`): create debt, add repayment, list with
  computed outstanding, settle, delete. Aggregation done in SQL.
- **Routes** (`app/api/routes.py`): new `/api/debts` endpoints (see below).
- **Schemas** (`app/schemas.py`): debt + repayment request/response models.
- **Localization** (`app/models/categories.py`): add `CATEGORY_LABELS_UZ`
  (income types already carry RU + UZ). Category/income endpoints return both
  `label_ru` and `label_uz`.

### Frontend (vanilla JS, no build step, no new deps)

- Extract the inline `<script>` from `templates/index.html` into
  `static/app.js` (cacheable, maintainable).
- New `static/i18n.js` — RU/UZ string dictionary + `t(key)` helper + toggle,
  choice stored in `localStorage`.
- `templates/index.html` restructured into **two tabs**:
  - `Hisobot` — existing dashboard (ring, category bars, add forms, ledger).
  - `Qarzlar` — debts view.

## Data model

```
debts                                  debt_repayments
─────                                  ───────────────
id              PK                     id               PK
user_id         FK users.id           debt_id          FK debts.id
counterparty    str (person name)      user_id          FK users.id
direction       'lent' | 'borrowed'    amount_uzs       int  (> 0)
principal_amount_uzs  int (> 0)        repayment_date   date
debt_date       date                   note             str? (<=1024)
note            str? (<=1024)          created_at
created_at
```

- `direction = 'lent'` → I gave money, **they owe me**.
- `direction = 'borrowed'` → I took money, **I owe them**.
- `outstanding = principal_amount_uzs − Σ repayments.amount_uzs`.
- A debt is **settled** when `outstanding == 0`.

**Indexes:**
- `debts`: `(user_id, direction)`, `(user_id, counterparty)`
- `debt_repayments`: `(debt_id)`, `(user_id, repayment_date)`

**Validation:**
- `principal_amount_uzs > 0`, `amount_uzs > 0`.
- A repayment may not exceed the current outstanding (no over-payment).
- `counterparty` required, trimmed, non-empty.

## API endpoints (new)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/debts` | List all debts with computed outstanding + repayments; grouped/orderable by direction. |
| POST | `/api/debts` | Create a debt (`counterparty`, `direction`, `principal_amount_uzs`, `debt_date`, `note?`). |
| PATCH | `/api/debts/{id}` | Edit a debt's fields. |
| DELETE | `/api/debts/{id}` | Delete a debt (cascades repayments). |
| POST | `/api/debts/{id}/repayments` | Add a repayment (validated ≤ outstanding). |
| DELETE | `/api/debts/{id}/repayments/{rid}` | Remove a repayment. |

All gated by the existing owner-header auth, consistent with current routes.

The `GET /api/debts` response also carries a `totals` block:
`lent_outstanding`, `borrowed_outstanding`, `net` (= lent − borrowed).

## Qarzlar UX

```
┌─────────────────────────────────────┐
│  Hisobot   ● Qarzlar        [RU|UZ]  │
├─────────────────────────────────────┤
│  Sof balans (Net)        +300 000    │
│  Menga qarzdor +500k · Men −200k     │
├─────────────────────────────────────┤
│  MENGA QARZDOR  (they owe me)        │
│  ┌─────────────────────────────────┐ │
│  │ Aziz              300 000  ▾     │ │
│  │ 500 000 · 01.06 · qoldi 300 000 │ │
│  │   ↳ −200 000 · 10.06            │ │
│  │   [+ to'lov]      [hal qilindi] │ │
│  └─────────────────────────────────┘ │
│  MEN QARZDORMAN  (I owe)             │
│  ┌─────────────────────────────────┐ │
│  │ Dilshod           200 000  ▾     │ │
│  └─────────────────────────────────┘ │
├─────────────────────────────────────┤
│   [ + Qarz berdim ]  [ + Qarz oldim ]│
└─────────────────────────────────────┘
```

- Two groups: **Menga qarzdor** (lent) and **Men qarzdorman** (borrowed).
- Net summary at top.
- Each debt card: counterparty, outstanding (primary), original + date,
  expandable repayment history; actions: **+ to'lov** (add repayment),
  **hal qilindi** (settle = repay remaining), edit, delete.
- Two add buttons: **Qarz berdim** (lent) / **Qarz oldim** (borrowed).
- Empty state per group when none.

## Bilingual (RU/UZ)

- `[RU|UZ]` segmented toggle in the header; choice in `localStorage`.
- `i18n.js` dictionary keyed by string id, both languages; `t(key)` returns the
  active-language string. Toggling re-renders in place — no reload, no refetch.
- Dynamic lists (categories, income types) ship both labels from the backend;
  the active label is chosen client-side.
- Number/date formatting stays locale-stable (UZS grouping, `dd.mm`).

## UI/UX polish (Hisobot tab)

- Consistent card system, spacing, and typography.
- Smoother spent-vs-saved ring with a subtle draw-in animation; refined
  empty / no-income / overspend states.
- Tab navigation between Hisobot and Qarzlar.
- Stays within the 480px mobile container; light/dark tokens preserved; no new
  dependencies.

## Logic & performance pass

- Parallelize the dashboard's startup fetches with `Promise.all` (today they run
  sequentially).
- Serve JS from a cached static file instead of re-sending it inline each load.
- Debounce month-refresh input.
- Add the debt indexes above; keep `func.sum`/`func.count` aggregation in SQL.

## Testing

- **Debts service:** create (lent/borrowed), partial repayment, over-payment
  rejection, outstanding computation, settle, delete (cascade), totals/net.
- **Validation:** positive amounts, required counterparty, valid dates.
- **Localization:** every category and income type has both RU and UZ labels;
  endpoints return both.
- Existing expense/income tests must continue to pass unchanged.

## Rollout / sequencing

The implementation plan will stage this as:
1. Backend qarz (models, service, schemas, routes, tests) — additive, no UI risk.
2. Frontend extraction (`app.js`) + tabs scaffold — no behavior change.
3. i18n layer (dictionary, toggle, UZ category labels).
4. Qarzlar tab UI wired to the API.
5. Hisobot polish + performance pass.

Each stage is independently verifiable; existing behavior is preserved throughout.
