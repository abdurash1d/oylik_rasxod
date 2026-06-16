# Qarz + Bilingual + Dashboard Redesign Implementation Plan

> **For agentic workers:** Implement task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. TDD for backend; commit after each task.

**Goal:** Add per-person debt tracking (qarz), a full RU/UZ language toggle, a tab-organized dashboard redesign, and a logic/perf pass to the rasxot_bot Telegram mini-app.

**Architecture:** Additive backend (new `debts`/`debt_repayments` tables + service + routes), extracted/refactored frontend (inline JS → `static/app.js`, new `static/i18n.js`), two-tab UI (Hisobot / Qarzlar). Existing expense/income behavior is preserved.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, PostgreSQL (SQLite for tests), Jinja2, vanilla JS, no new dependencies.

---

## Stage 1 — Backend: Qarz (debts)

### Task 1: Debt + DebtRepayment models

**Files:**
- Create: `app/models/debt.py`
- Modify: `app/models/__init__.py`, `app/main.py` (model import for `create_all`)

- [ ] **Step 1:** Create `app/models/debt.py` with `Debt` (id, user_id FK, counterparty str(255), direction str(16) `'lent'|'borrowed'`, principal_amount_uzs int, debt_date date, note str(1024)?, created_at) and `DebtRepayment` (id, debt_id FK→debts.id `ondelete=CASCADE`, user_id FK, amount_uzs int, repayment_date date, note str(1024)?, created_at). Add a `repayments` relationship on `Debt` with `cascade="all, delete-orphan"`. Indexes: `ix_debts_user_direction (user_id, direction)`, `ix_debts_user_counterparty (user_id, counterparty)`, `ix_debt_repayments_debt (debt_id)`, `ix_debt_repayments_user_date (user_id, repayment_date)`.
- [ ] **Step 2:** Export `Debt`, `DebtRepayment` from `app/models/__init__.py`; add to `app/main.py` noqa import so `Base.metadata.create_all` builds the tables.
- [ ] **Step 3:** Commit `feat: add Debt and DebtRepayment models`.

### Task 2: Debt schemas

**Files:** Modify `app/schemas.py`

- [ ] Add `DebtDirection` literal handling (`"lent"`, `"borrowed"`). Add schemas:
  - `DebtCreate` (counterparty trimmed non-empty, direction validated, principal_amount_uzs gt=0, debt_date, note?)
  - `DebtUpdate` (all optional, same validators)
  - `RepaymentCreate` (amount_uzs gt=0, repayment_date, note?)
  - `RepaymentOut` (id, amount_uzs, repayment_date, note)
  - `DebtOut` (id, counterparty, direction, principal_amount_uzs, debt_date, note, outstanding_uzs, settled bool, repayments: List[RepaymentOut])
  - `DebtTotals` (lent_outstanding, borrowed_outstanding, net)
  - `DebtsResponse` (debts: List[DebtOut], totals: DebtTotals)
- [ ] Commit `feat: add debt schemas`.

### Task 3: Debt service (TDD)

**Files:**
- Create: `app/services/debts.py`
- Test: `tests/test_debts.py`

- [ ] **Step 1 (failing test):** `tests/test_debts.py` — in-memory SQLite, create user, `create_debt` (lent 500000), `add_repayment` 200000 → `list_debts` shows outstanding 300000, settled False, totals.lent_outstanding 300000, net 300000. Over-payment (repay 400000 on 300000 outstanding) raises `ValueError`. `settle_debt` repays remaining → outstanding 0, settled True. `delete_debt` cascades repayments.
- [ ] **Step 2:** Run `pytest tests/test_debts.py -v` → FAIL (module missing).
- [ ] **Step 3 (implement):** `app/services/debts.py`:
  - `create_debt(db, user_id, payload) -> Debt`
  - `add_repayment(db, user_id, debt_id, payload) -> DebtRepayment` — loads debt (scoped to user), computes outstanding = principal − Σ repayments; raises `ValueError("Debt not found")` / `ValueError("Repayment exceeds outstanding")`.
  - `_outstanding(debt) -> int` helper.
  - `list_debts(db, user_id) -> DebtsResponse` — single query loading debts with repayments (use `selectinload(Debt.repayments)` to avoid N+1); builds `DebtOut` + totals.
  - `update_debt`, `delete_debt`, `delete_repayment`, `settle_debt`.
- [ ] **Step 4:** Run tests → PASS.
- [ ] **Step 5:** Commit `feat: add debt service with repayment logic`.

### Task 4: Debt routes

**Files:** Modify `app/api/routes.py`

- [ ] Add endpoints (owner-gated via existing `owner_user`): `GET /api/debts`, `POST /api/debts`, `PATCH /api/debts/{id}`, `DELETE /api/debts/{id}`, `POST /api/debts/{id}/repayments`, `DELETE /api/debts/{id}/repayments/{rid}`. Map `ValueError("...not found")` → 404, `ValueError("Repayment exceeds outstanding")` → 400.
- [ ] Commit `feat: add debt API routes`.

---

## Stage 2 — Bilingual backend labels

### Task 5: Uzbek category labels

**Files:** Modify `app/models/categories.py`, `app/schemas.py`, `app/api/routes.py`, `app/services/expenses.py`

- [ ] Add `CATEGORY_LABELS_UZ` for all 10 keys; `category_options()` returns `label_uz` too. Add `label_uz` to `CategorySummary`, `ExpenseOut`, `LedgerRow` (and populate in service/routes). Income already has UZ.
- [ ] Update `tests/test_categories.py` expectation if it asserts option shape; run full suite green.
- [ ] Commit `feat: add Uzbek labels to categories and responses`.

---

## Stage 3 — Frontend refactor: extract JS, i18n, tabs scaffold

### Task 6: Extract inline JS → static/app.js (no behavior change)

**Files:** Create `app/static/app.js`; modify `app/templates/index.html`

- [ ] Move the entire `<script>` body into `app/static/app.js`. In the template, replace inline script with `<script>window.APP_CONFIG={apiBase:"{{ api_base }}",year:{{ year }},month:{{ month }}};</script>` then `<script src="/static/app.js" defer></script>`. Read `apiBase` from `APP_CONFIG`.
- [ ] Manually verify dashboard still loads (run app, open `/app`). Commit `refactor: extract dashboard JS to static/app.js`.

### Task 7: i18n module + language toggle

**Files:** Create `app/static/i18n.js`; modify `index.html`, `app/static/app.js`, `styles.css`

- [ ] `i18n.js`: `const STRINGS = { ru:{...}, uz:{...} }` covering every UI string (tabs, ring labels, form labels, buttons, statuses, qarz strings). `let lang = localStorage.getItem('lang') || 'ru'`. `function t(key){...}`, `function setLang(l){...}`, `function getLang(){...}`. Expose on `window.i18n`.
- [ ] Add `[RU|UZ]` toggle to header in `index.html`; all static text gets `data-i18n="key"` attributes; `app.js` has `applyI18n()` that fills them and re-renders dynamic content on toggle (dropdown labels pick `label_ru`/`label_uz` by `getLang()`).
- [ ] Commit `feat: add RU/UZ i18n layer and language toggle`.

### Task 8: Two-tab shell (Hisobot / Qarzlar)

**Files:** Modify `index.html`, `app.js`, `styles.css`

- [ ] Wrap existing dashboard in `<section id="tab-hisobot">`; add empty `<section id="tab-qarzlar" hidden>`. Add tab bar with two buttons; `app.js` `setupTabs()` toggles `hidden` + active state; lazy-load qarz data on first Qarzlar open.
- [ ] Commit `feat: add Hisobot/Qarzlar tab shell`.

---

## Stage 4 — Qarzlar tab UI

### Task 9: Qarzlar rendering + forms wired to API

**Files:** Modify `index.html`, `app.js`, `styles.css`

- [ ] Build Qarzlar markup: net summary, two groups (lent / borrowed), debt cards with outstanding, expandable repayment history, `+ to'lov` / settle / edit / delete actions, and `+ Qarz berdim` / `+ Qarz oldim` add forms (modal or inline panel). `app.js`: `loadDebts()`, `renderDebts(data)`, add/repay/settle/delete handlers calling the Stage 1 endpoints; refresh on change. All labels via `t()`.
- [ ] Commit `feat: implement Qarzlar tab UI`.

---

## Stage 5 — Hisobot polish + performance

### Task 10: Visual polish + perf pass

**Files:** Modify `styles.css`, `app.js`, `index.html`

- [ ] CSS polish: refined cards/spacing/typography, ring draw-in animation (`@keyframes`), improved empty/overspend states, tab-bar and qarz styles consistent with tokens; keep 480px container, light/dark, focus rings.
- [ ] Perf: confirm `refreshAll` uses `Promise.all` (already does); debounce month inputs (300ms) to auto-refresh; `app.js` served `defer` + cached. Keep aggregation in SQL.
- [ ] Commit `feat: polish Hisobot dashboard and performance pass`.

### Task 11: Final verification

- [ ] Run `pytest -q` → all green. Manually load `/app`, toggle RU/UZ, switch tabs, add a lent + borrowed debt, add a partial repayment, settle one, delete one.
- [ ] Update bot `/help` text in `app.py` to mention Qarzlar (RU+UZ). Commit `docs: mention qarzlar in /help`.

---

## Self-review notes
- Spec coverage: qarz model/UX (Tasks 1-4, 9), bilingual (Tasks 5, 7), redesign (Tasks 8, 10), perf/logic (Tasks 6, 10). ✔
- Types consistent: `DebtOut.outstanding_uzs`, `DebtTotals.net`, service `_outstanding`, `list_debts` used uniformly.
- No placeholders; each task independently committable and existing tests stay green.
