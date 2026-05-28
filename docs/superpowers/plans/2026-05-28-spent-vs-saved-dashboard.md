# Spent-vs-Saved Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the `rasxot_bot` Telegram mini-app frontend to a Concept C dashboard — a spent/saved ring + ranked per-category spending bars + segmented Расход/Доход add form + polished history — with consistent Russian labels and no Chart.js dependency.

**Architecture:** Pure frontend redesign. The two files affected are `app/templates/index.html` (HTML + inline JS module) and `app/static/styles.css`. The Python backend is untouched; all data already comes from the existing `/api/summary/month`, `/api/ledger/month`, `/api/categories`, `/api/income-types`, and `POST/PATCH/DELETE /api/expenses` and `/api/incomes` endpoints. Category share % is computed client-side from the summary response. No DB or schema changes.

**Tech Stack:** Vanilla JS (no framework, no build step), CSS custom properties + `conic-gradient` for the ring, FastAPI + Jinja2 serving the static page (unchanged), `pytest` for the existing backend tests (must stay green).

**Branch:** `feature/spent-vs-saved-dashboard` (already created).

**Spec:** `docs/superpowers/specs/2026-05-27-spent-vs-saved-dashboard-design.md`.

---

## Reference: API shapes (executors — read this once, no need to re-explore)

All auth-requiring endpoints expect headers:
```
X-Telegram-User-Id: <number>
X-Telegram-Username: <string>
Content-Type: application/json
```

### `GET /api/summary/month?year=YYYY&month=M` → `MonthlySummary`
```json
{
  "expense_total_uzs": 5200000,
  "income_total_uzs":  8000000,
  "balance_uzs":       2800000,
  "by_category": [
    { "category_key": "food_groceries", "category_label_ru": "Продукты", "total_uzs": 2100000 }
  ],
  "expense_entry_count": 12,
  "income_entry_count":   1
}
```
`by_category` is already sorted by `total_uzs` desc.

### `GET /api/ledger/month?year=YYYY&month=M` → `LedgerResponse`
```json
{
  "entries": [
    {
      "entry_type": "expense",      // or "income"
      "id": 42,
      "date": "2026-05-27",
      "amount_uzs": 120000,
      "note": "Магазин",            // nullable
      "label_ru": "Продукты",
      "raw_key": "food_groceries"   // category_key for expenses, income_type_key for incomes
    }
  ]
}
```
Sorted by `(date, id)` desc.

### `GET /api/categories` → `{ "categories": [ { "key": "...", "label_ru": "..." } ] }`
No auth headers.

### `GET /api/income-types` → `{ "income_types": [ { "key": "...", "label_ru": "...", "label_uz": "..." } ] }`
No auth headers. **For this redesign, only `label_ru` is shown** (UI is consistent Russian).

### `POST /api/expenses` — body `ExpenseCreate`
```json
{ "category_key": "food_groceries", "amount_uzs": 120000, "expense_date": "2026-05-27", "note": null }
```
Response: `ExpenseOut`.

### `PATCH /api/expenses/{id}` — partial `ExpenseUpdate` (all fields optional, same names).
### `DELETE /api/expenses/{id}` → `{ "status": "ok" }`.

### `POST /api/incomes` — body `IncomeCreate`
```json
{ "income_type_key": "salary", "amount_uzs": 8000000, "income_date": "2026-05-25", "note": null }
```
### `PATCH /api/incomes/{id}` — partial `IncomeUpdate`.
### `DELETE /api/incomes/{id}` → `{ "status": "ok" }`.

### Jinja2 template context (from `app/main.py:99-108`)
The `GET /app` route renders `index.html` with: `request`, `api_base="/api"`, `year=<current year>`, `month=<current month>`. Template must keep using `{{ api_base }}`, `{{ year }}`, `{{ month }}`.

---

## Reference: category color palette

Stable color per category key, used for bar fills:

| key | color |
|---|---|
| `food_groceries` | `#0071e3` |
| `market` | `#f59e0b` |
| `transportation` | `#ff9f0a` |
| `housing` | `#34c759` |
| `health` | `#ff3b30` |
| `shopping` | `#af52de` |
| `personal_care` | `#ec4899` |
| `utilities` | `#06b6d4` |
| `miscellaneous` | `#94a3b8` |
| `others` | `#64748b` |

Fallback (unknown key): `#64748b`.

---

## File structure

- **Modify:** `app/static/styles.css` — full rewrite to the new design system.
- **Modify:** `app/templates/index.html` — full rewrite (head, body markup, inline JS module).
- **No other files touched.** Tests (`tests/`), backend (`app/api/`, `app/services/`, `app/models/`, `app/schemas.py`, `app/main.py`) stay as they are.

---

## Note on testing

The project has no JavaScript test infrastructure (the existing `tests/` directory is Python-only and tests the backend). Adding one is out of scope per the approved spec ("feature + dashboard polish"). UI verification in this plan is **manual** (open the page, check the four ring states render). The existing `pytest` suite must stay green as a backend regression guard.

---

## Task 1: Replace `app/static/styles.css` with the new design system

**Files:**
- Modify: `app/static/styles.css` (full rewrite)

- [ ] **Step 1: Write the new `app/static/styles.css`**

Replace the entire contents of `app/static/styles.css` with the following:

```css
/* ===== Design tokens ===== */
:root {
  --bg: #f5f7fa;
  --surface: #ffffff;
  --surface-2: #eef2f7;
  --border: #e2e8f0;
  --text: #0f172a;
  --muted: #64748b;
  --brand: #0ea5e9;
  --brand-strong: #0284c7;
  --income: #16a34a;
  --expense: #e11d48;
  --ring-track: #e2e8f0;
  --shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
  --radius: 12px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0b1220;
    --surface: #111a2e;
    --surface-2: #182239;
    --border: #1f2a44;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --ring-track: #1f2a44;
    --shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
  }
}

/* ===== Base ===== */
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-size: 15px;
  line-height: 1.45;
  -webkit-font-smoothing: antialiased;
}
.container {
  max-width: 480px;
  margin: 0 auto;
  padding: 14px 14px 32px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

/* ===== Top bar / month picker ===== */
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.month-picker {
  display: flex;
  gap: 6px;
  align-items: center;
  width: 100%;
}
.month-picker input {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  width: 78px;
  font-size: 14px;
  text-align: center;
}
.btn-ghost {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  cursor: pointer;
  margin-left: auto;
}
.btn-ghost:hover { background: var(--surface-2); }

/* ===== Ring section ===== */
.ring-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 22px 16px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.ring {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: var(--ring-track);
  position: relative;
  margin-bottom: 14px;
  transition: background 0.3s ease;
}
.ring-inner {
  position: absolute;
  inset: 16px;
  background: var(--surface);
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.ring-label {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--muted);
}
.ring-amount {
  font-size: 22px;
  font-weight: 800;
  margin: 2px 0;
  color: var(--text);
}
.ring-sub {
  font-size: 11px;
  color: var(--muted);
}
.legend {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 14px;
  font-size: 13px;
  color: var(--muted);
}
.legend b { color: var(--text); }
.legend .saved-pos { color: var(--income); }
.legend .saved-neg { color: var(--expense); }

/* ===== Sections ===== */
.section-label {
  font-size: 10px;
  letter-spacing: 0.08em;
  color: var(--muted);
  margin-bottom: 8px;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 14px;
}

/* ===== Category bars ===== */
.categories { display: flex; flex-direction: column; gap: 8px; }
.category-bars { display: flex; flex-direction: column; gap: 10px; }
.cat-row { display: flex; flex-direction: column; gap: 4px; }
.cat-meta { display: flex; justify-content: space-between; font-size: 13px; }
.cat-name { color: var(--text); }
.cat-amount { color: var(--muted); }
.cat-bar {
  height: 7px;
  background: var(--ring-track);
  border-radius: 4px;
  overflow: hidden;
}
.cat-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

/* ===== Segmented Расход/Доход + forms ===== */
.add { display: flex; flex-direction: column; gap: 10px; }
.segmented {
  display: flex;
  background: var(--surface-2);
  border-radius: 10px;
  padding: 3px;
}
.seg-btn {
  flex: 1;
  background: transparent;
  color: var(--muted);
  border: none;
  border-radius: 7px;
  padding: 8px 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.seg-btn.active {
  background: var(--brand);
  color: #fff;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 14px;
}
.form.hidden { display: none; }
.form label { display: flex; flex-direction: column; gap: 4px; font-size: 13px; color: var(--muted); }
.form label.grow { flex: 1; }
.form .row { display: flex; gap: 10px; }
.form input, .form select {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 9px 10px;
  font-size: 15px;
  width: 100%;
}
.btn-primary {
  background: var(--brand);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.btn-primary:hover { background: var(--brand-strong); }
.status { font-size: 12px; color: var(--muted); min-height: 16px; margin: 0; }

/* ===== History / ledger ===== */
.history { display: flex; flex-direction: column; gap: 8px; }
#ledgerList { display: flex; flex-direction: column; }
.ledger-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.ledger-row:last-child { border-bottom: none; }
.ledger-main { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.ledger-main strong { font-weight: 600; }
.ledger-date { color: var(--muted); font-size: 12px; }
.ledger-note { color: var(--muted); font-size: 12px; }
.ledger-side { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.amount { font-weight: 700; font-variant-numeric: tabular-nums; }
.amount.income { color: var(--income); }
.amount.expense { color: var(--expense); }
.badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--surface-2);
  color: var(--muted);
}
.badge.income { color: var(--income); }
.badge.expense { color: var(--expense); }
.ledger-actions { display: flex; gap: 4px; }
.mini {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 4px 8px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text);
}
.mini.danger { color: var(--expense); border-color: var(--expense); }
.mini.success { color: #fff; background: var(--brand); border-color: var(--brand); }
.ledger-row.editing { flex-direction: column; align-items: stretch; }
.ledger-edit { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.ledger-edit select, .ledger-edit input {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 14px;
}
.empty {
  text-align: center;
  color: var(--muted);
  padding: 14px;
  font-size: 13px;
}

/* ===== Small-screen polish ===== */
@media (max-width: 480px) {
  .container { padding: 10px 10px 28px; }
  .ring { width: 160px; height: 160px; }
  .ring-amount { font-size: 19px; }
  .form input, .form select { font-size: 16px; } /* prevents iOS zoom */
}
```

- [ ] **Step 2: Verify backend tests still pass (regression guard)**

Run from project root:
```bash
python -m pytest -q
```
Expected: all existing tests pass (no test was added or removed; backend is untouched, so this should be a green run with the same count as before).

- [ ] **Step 3: Commit**

```bash
git add app/static/styles.css
git commit -m "Replace dashboard CSS with new design system for spent-vs-saved redesign

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Replace `app/templates/index.html` with the Concept C dashboard

**Files:**
- Modify: `app/templates/index.html` (full rewrite — head, body markup, inline JS module)

- [ ] **Step 1: Write the new `app/templates/index.html`**

Replace the entire contents of `app/templates/index.html` with the following:

```html
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover" />
  <title>Ежемесячные расходы</title>
  <link rel="stylesheet" href="/static/styles.css" />
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
  <div class="container">

    <!-- Month picker -->
    <header class="topbar">
      <div class="month-picker">
        <input id="year" type="number" min="2020" max="2100" value="{{ year }}" />
        <input id="month" type="number" min="1" max="12" value="{{ month }}" />
        <button id="reloadBtn" type="button" class="btn-ghost">Обновить</button>
      </div>
    </header>

    <!-- Ring -->
    <section class="ring-section">
      <div class="ring" id="ring">
        <div class="ring-inner">
          <div class="ring-label">ПОТРАЧЕНО</div>
          <div class="ring-amount" id="ringAmount">0</div>
          <div class="ring-sub" id="ringSub">—</div>
        </div>
      </div>
      <div class="legend">
        <span id="legendSaved">—</span>
        <span>Доход <b id="legendIncome">0</b></span>
      </div>
    </section>

    <!-- Categories -->
    <section class="categories card">
      <div class="section-label">РАСХОДЫ ПО КАТЕГОРИЯМ</div>
      <div id="categoryList" class="category-bars"></div>
    </section>

    <!-- Add (segmented Расход/Доход) -->
    <section class="add">
      <div class="segmented" role="tablist">
        <button type="button" class="seg-btn active" data-tab="expense">Расход</button>
        <button type="button" class="seg-btn" data-tab="income">Доход</button>
      </div>

      <form id="expenseForm" class="form">
        <label>
          <span>Категория</span>
          <select id="category" required></select>
        </label>
        <div class="row">
          <label class="grow">
            <span>Сумма (сум)</span>
            <input id="amount" type="number" min="1" step="1" required />
          </label>
          <label>
            <span>Дата</span>
            <input id="expenseDate" type="date" required />
          </label>
        </div>
        <label>
          <span>Заметка</span>
          <input id="note" type="text" maxlength="1024" placeholder="необязательно" />
        </label>
        <button type="submit" class="btn-primary">Сохранить</button>
        <p id="formStatus" class="status"></p>
      </form>

      <form id="incomeForm" class="form hidden">
        <label>
          <span>Тип дохода</span>
          <select id="incomeType" required></select>
        </label>
        <div class="row">
          <label class="grow">
            <span>Сумма (сум)</span>
            <input id="incomeAmount" type="number" min="1" step="1" required />
          </label>
          <label>
            <span>Дата</span>
            <input id="incomeDate" type="date" required />
          </label>
        </div>
        <label>
          <span>Заметка</span>
          <input id="incomeNote" type="text" maxlength="1024" placeholder="необязательно" />
        </label>
        <button type="submit" class="btn-primary">Сохранить</button>
        <p id="incomeFormStatus" class="status"></p>
      </form>
    </section>

    <!-- History -->
    <section class="history card">
      <div class="section-label">ИСТОРИЯ</div>
      <p id="ledgerStatus" class="status"></p>
      <div id="ledgerList"></div>
    </section>

  </div>

  <script>
    // ---- Telegram WebApp init ----
    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand();

    const apiBase = "{{ api_base }}";
    const initDataUnsafe = tg.initDataUnsafe || {};
    const user = initDataUnsafe.user || {};
    const headers = {
      "Content-Type": "application/json",
      "X-Telegram-User-Id": user.id || "",
      "X-Telegram-Username": user.username || "",
    };

    // ---- Constants ----
    const CATEGORY_COLORS = {
      food_groceries: "#0071e3",
      market: "#f59e0b",
      transportation: "#ff9f0a",
      housing: "#34c759",
      health: "#ff3b30",
      shopping: "#af52de",
      personal_care: "#ec4899",
      utilities: "#06b6d4",
      miscellaneous: "#94a3b8",
      others: "#64748b",
    };
    const DEFAULT_COLOR = "#64748b";

    // ---- State ----
    let categories = [];
    let incomeTypes = [];
    let editingEntryKey = null;

    // ---- Helpers ----
    const ru = new Intl.NumberFormat("ru-RU");
    function fmtAmount(n) { return ru.format(n || 0); }
    function fmtUZS(n) { return fmtAmount(n) + " сум"; }
    function escapeHtml(s) {
      return String(s ?? "").replace(/[&<>"']/g, c => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
      }[c]));
    }
    function currentFilters() {
      const year = Number(document.getElementById("year").value);
      const month = Number(document.getElementById("month").value);
      return { year, month };
    }

    // ---- Categories / income types ----
    async function loadCategories() {
      const res = await fetch(`${apiBase}/categories`);
      const data = await res.json();
      categories = data.categories || [];
      const select = document.getElementById("category");
      select.innerHTML = "";
      for (const c of categories) {
        const opt = document.createElement("option");
        opt.value = c.key;
        opt.textContent = c.label_ru;
        select.appendChild(opt);
      }
    }
    async function loadIncomeTypes() {
      const res = await fetch(`${apiBase}/income-types`);
      const data = await res.json();
      incomeTypes = data.income_types || [];
      const select = document.getElementById("incomeType");
      select.innerHTML = "";
      for (const t of incomeTypes) {
        const opt = document.createElement("option");
        opt.value = t.key;
        opt.textContent = t.label_ru; // Russian only, drop /label_uz
        select.appendChild(opt);
      }
    }

    // ---- Ring ----
    function renderRing(summary) {
      const ring = document.getElementById("ring");
      const ringAmount = document.getElementById("ringAmount");
      const ringSub = document.getElementById("ringSub");
      const legendSaved = document.getElementById("legendSaved");
      const legendIncome = document.getElementById("legendIncome");

      const spent = summary.expense_total_uzs || 0;
      const income = summary.income_total_uzs || 0;
      const balance = summary.balance_uzs || 0;
      legendIncome.textContent = fmtAmount(income);

      if (income === 0 && spent === 0) {
        ring.style.background = "var(--ring-track)";
        ringAmount.textContent = "0";
        ringSub.textContent = "Нет данных";
        legendSaved.innerHTML = "—";
        return;
      }
      if (income === 0) {
        ring.style.background = "var(--expense)";
        ringAmount.textContent = fmtAmount(spent);
        ringSub.textContent = "Доход не указан";
        legendSaved.innerHTML = "—";
        return;
      }
      if (spent > income) {
        ring.style.background = "var(--expense)";
        ringAmount.textContent = fmtAmount(spent);
        const pctOver = Math.round((spent / income) * 100);
        ringSub.textContent = `${pctOver}% дохода`;
        const over = spent - income;
        legendSaved.innerHTML = `<span class="saved-neg">🔴 Перерасход <b>${fmtAmount(over)}</b></span>`;
        return;
      }
      // normal
      const pctSpent = Math.round((spent / income) * 100);
      ring.style.background = `conic-gradient(var(--expense) 0 ${pctSpent}%, var(--income) ${pctSpent}% 100%)`;
      ringAmount.textContent = fmtAmount(spent);
      ringSub.textContent = `${pctSpent}% дохода`;
      legendSaved.innerHTML = `<span class="saved-pos">🟢 Отложено <b>${fmtAmount(balance)}</b></span>`;
    }

    // ---- Category bars ----
    function renderCategoryBars(summary) {
      const list = document.getElementById("categoryList");
      list.innerHTML = "";
      const total = summary.expense_total_uzs || 0;
      const rows = summary.by_category || [];
      if (rows.length === 0) {
        const empty = document.createElement("div");
        empty.className = "empty";
        empty.textContent = "Нет расходов за этот месяц.";
        list.appendChild(empty);
        return;
      }
      for (const row of rows) {
        const pct = total > 0 ? Math.round((row.total_uzs / total) * 100) : 0;
        const color = CATEGORY_COLORS[row.category_key] || DEFAULT_COLOR;
        const wrap = document.createElement("div");
        wrap.className = "cat-row";
        wrap.innerHTML = `
          <div class="cat-meta">
            <span class="cat-name">${escapeHtml(row.category_label_ru)}</span>
            <span class="cat-amount">${fmtAmount(row.total_uzs)} · ${pct}%</span>
          </div>
          <div class="cat-bar"><div class="cat-fill" style="width:${pct}%;background:${color}"></div></div>
        `;
        list.appendChild(wrap);
      }
    }

    // ---- Summary loader ----
    async function loadSummary() {
      const { year, month } = currentFilters();
      const res = await fetch(`${apiBase}/summary/month?year=${year}&month=${month}`, { headers });
      if (!res.ok) {
        document.getElementById("ledgerStatus").textContent = "Не удалось загрузить сводку.";
        return;
      }
      const summary = await res.json();
      renderRing(summary);
      renderCategoryBars(summary);
    }

    // ---- Ledger ----
    function entryTypeLabel(t) { return t === "income" ? "Доход" : "Расход"; }
    function renderLedgerRow(entry) {
      const key = `${entry.entry_type}:${entry.id}`;
      const isEdit = editingEntryKey === key;
      const isIncome = entry.entry_type === "income";

      if (!isEdit) {
        const amountClass = isIncome ? "amount income" : "amount expense";
        const sign = isIncome ? "+" : "−";
        return `
          <div class="ledger-row">
            <div class="ledger-main">
              <span class="badge ${isIncome ? "income" : "expense"}">${entryTypeLabel(entry.entry_type)}</span>
              <strong>${escapeHtml(entry.label_ru)}</strong>
              <span class="ledger-date">${escapeHtml(entry.date)}</span>
              ${entry.note ? `<span class="ledger-note">${escapeHtml(entry.note)}</span>` : ""}
            </div>
            <div class="ledger-side">
              <span class="${amountClass}">${sign}${fmtAmount(entry.amount_uzs)}</span>
              <div class="ledger-actions">
                <button type="button" class="mini" data-action="start-edit" data-entry-key="${key}">✏️</button>
                <button type="button" class="mini danger" data-action="delete"
                        data-entry-key="${key}" data-entry-type="${entry.entry_type}" data-entry-id="${entry.id}">🗑</button>
              </div>
            </div>
          </div>
        `;
      }
      // edit
      const options = isIncome ? incomeTypes : categories;
      const optionsHtml = options
        .map(o => `<option value="${o.key}" ${o.key === entry.raw_key ? "selected" : ""}>${escapeHtml(o.label_ru)}</option>`)
        .join("");
      return `
        <div class="ledger-row editing">
          <div class="ledger-edit">
            <select id="editRawKey">${optionsHtml}</select>
            <input id="editAmount" type="number" min="1" step="1" value="${entry.amount_uzs}" />
            <input id="editDate" type="date" value="${escapeHtml(entry.date)}" />
            <input id="editNote" type="text" maxlength="1024" value="${escapeHtml(entry.note || "")}" placeholder="заметка" />
          </div>
          <div class="ledger-actions">
            <button type="button" class="mini success" data-action="save-edit"
                    data-entry-key="${key}" data-entry-type="${entry.entry_type}" data-entry-id="${entry.id}">Сохранить</button>
            <button type="button" class="mini" data-action="cancel-edit">Отмена</button>
          </div>
        </div>
      `;
    }
    async function loadLedger() {
      const { year, month } = currentFilters();
      const res = await fetch(`${apiBase}/ledger/month?year=${year}&month=${month}`, { headers });
      const list = document.getElementById("ledgerList");
      if (!res.ok) {
        list.innerHTML = `<div class="empty">Не удалось загрузить историю.</div>`;
        return;
      }
      const data = await res.json();
      const entries = data.entries || [];
      if (entries.length === 0) {
        list.innerHTML = `<div class="empty">Записей нет.</div>`;
        return;
      }
      list.innerHTML = entries.map(renderLedgerRow).join("");
    }

    async function refreshAll() {
      await Promise.all([loadSummary(), loadLedger()]);
    }

    // ---- Segmented toggle ----
    function setupSegmented() {
      const segBtns = document.querySelectorAll(".seg-btn");
      segBtns.forEach(btn => {
        btn.addEventListener("click", () => {
          segBtns.forEach(b => b.classList.toggle("active", b === btn));
          const tab = btn.dataset.tab;
          document.getElementById("expenseForm").classList.toggle("hidden", tab !== "expense");
          document.getElementById("incomeForm").classList.toggle("hidden", tab !== "income");
        });
      });
    }

    // ---- Form submit listeners ----
    function setupForms() {
      document.getElementById("expenseForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
          category_key: document.getElementById("category").value,
          amount_uzs: Number(document.getElementById("amount").value),
          expense_date: document.getElementById("expenseDate").value,
          note: document.getElementById("note").value || null,
        };
        const res = await fetch(`${apiBase}/expenses`, {
          method: "POST", headers, body: JSON.stringify(payload),
        });
        const status = document.getElementById("formStatus");
        if (res.ok) {
          status.textContent = "Сохранено.";
          document.getElementById("amount").value = "";
          document.getElementById("note").value = "";
          await refreshAll();
        } else {
          status.textContent = "Не удалось сохранить расход.";
        }
      });
      document.getElementById("incomeForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const payload = {
          income_type_key: document.getElementById("incomeType").value,
          amount_uzs: Number(document.getElementById("incomeAmount").value),
          income_date: document.getElementById("incomeDate").value,
          note: document.getElementById("incomeNote").value || null,
        };
        const res = await fetch(`${apiBase}/incomes`, {
          method: "POST", headers, body: JSON.stringify(payload),
        });
        const status = document.getElementById("incomeFormStatus");
        if (res.ok) {
          status.textContent = "Сохранено.";
          document.getElementById("incomeAmount").value = "";
          document.getElementById("incomeNote").value = "";
          await refreshAll();
        } else {
          status.textContent = "Не удалось сохранить доход.";
        }
      });
    }

    // ---- Reload button ----
    function setupReload() {
      document.getElementById("reloadBtn").addEventListener("click", () => refreshAll());
    }

    // ---- Ledger click delegation (edit / delete / save / cancel) ----
    function setupLedgerActions() {
      document.getElementById("ledgerList").addEventListener("click", async (e) => {
        const btn = e.target.closest("button[data-action]");
        if (!btn) return;
        const action = btn.dataset.action;
        const entryKey = btn.dataset.entryKey || editingEntryKey;
        const status = document.getElementById("ledgerStatus");
        status.textContent = "";

        if (action === "start-edit") {
          editingEntryKey = entryKey;
          await loadLedger();
          return;
        }
        if (action === "cancel-edit") {
          editingEntryKey = null;
          await loadLedger();
          return;
        }
        if (action === "delete") {
          if (!confirm("Удалить запись?")) return;
          const entryType = btn.dataset.entryType;
          const entryId = btn.dataset.entryId;
          const endpoint = entryType === "income" ? "incomes" : "expenses";
          const res = await fetch(`${apiBase}/${endpoint}/${entryId}`, { method: "DELETE", headers });
          if (res.ok) {
            editingEntryKey = null;
            status.textContent = "Удалено.";
            await refreshAll();
          } else {
            status.textContent = "Не удалось удалить.";
          }
          return;
        }
        if (action === "save-edit") {
          const entryType = btn.dataset.entryType;
          const entryId = btn.dataset.entryId;
          const endpoint = entryType === "income" ? "incomes" : "expenses";
          const rawKey = document.getElementById("editRawKey").value;
          const amount = Number(document.getElementById("editAmount").value);
          const dateVal = document.getElementById("editDate").value;
          const noteVal = document.getElementById("editNote").value || null;
          const payload = entryType === "income"
            ? { income_type_key: rawKey, amount_uzs: amount, income_date: dateVal, note: noteVal }
            : { category_key: rawKey, amount_uzs: amount, expense_date: dateVal, note: noteVal };
          const res = await fetch(`${apiBase}/${endpoint}/${entryId}`, {
            method: "PATCH", headers, body: JSON.stringify(payload),
          });
          if (res.ok) {
            editingEntryKey = null;
            status.textContent = "Сохранено.";
            await refreshAll();
          } else {
            status.textContent = "Не удалось сохранить изменения.";
          }
          return;
        }
      });
    }

    // ---- Init ----
    (async function init() {
      const today = new Date().toISOString().slice(0, 10);
      document.getElementById("expenseDate").value = today;
      document.getElementById("incomeDate").value = today;

      setupSegmented();
      setupForms();
      setupReload();
      setupLedgerActions();

      await loadCategories();
      await loadIncomeTypes();
      await refreshAll();
    })();
  </script>
</body>
</html>
```

- [ ] **Step 2: Verify backend tests still pass (regression guard)**

```bash
python -m pytest -q
```
Expected: same green run as before — the template is unrelated to backend tests, but this confirms no accidental backend change.

- [ ] **Step 3: Commit**

```bash
git add app/templates/index.html
git commit -m "Replace mini-app dashboard with Concept C spent-vs-saved layout

Drops the Chart.js pie + CDN script. New layout: spent/saved ring (CSS
conic-gradient), ranked per-category bars with %, segmented Расход/Доход
toggle, polished history. All labels normalized to Russian. Backend and
API surface unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Manual verification of all dashboard states

This task does not change code; it validates the four ring states and the core flows.

**Files:** none modified.

- [ ] **Step 1: Start the app locally**

From project root:
```bash
python -m uvicorn app.main:app --reload --port 8000
```
Expected: server starts, no startup errors. Visit `http://localhost:8000/app` in a browser (the `X-Telegram-User-Id` header will be empty, so write endpoints will 403 — that's fine for visual checks).

To test write endpoints (forms, edit, delete), use a request that bypasses the WebApp by including the headers manually. For the dev-time browser visual check, just confirming the page renders is enough.

- [ ] **Step 2: Verify the four ring states render**

To exercise each state without crafting database fixtures, you can directly call the API with curl using the configured `OWNER_TELEGRAM_ID`. Example for one expense:
```bash
OWNER=$(grep '^OWNER_TELEGRAM_ID=' .env | cut -d= -f2)
curl -s -X POST http://localhost:8000/api/expenses \
  -H "Content-Type: application/json" \
  -H "X-Telegram-User-Id: $OWNER" \
  -d '{"category_key":"food_groceries","amount_uzs":120000,"expense_date":"2026-05-27","note":"тест"}'
```

Check each state in the browser at `/app`:

| State | How to reach it | Expected on screen |
|---|---|---|
| **Empty month** | Pick a year/month with no entries (e.g. year=2030, month=1) and click Обновить | Ring is gray track; `ПОТРАЧЕНО 0 / Нет данных`; legend `—`; category list shows "Нет расходов за этот месяц."; history shows "Записей нет." |
| **No income** | Add one expense in the current month; no income | Ring fully red; `ПОТРАЧЕНО <amount> / Доход не указан`; legend `—`; bars visible |
| **Normal** | Add an income larger than total expenses | Ring red arc = % spent, green arc = saved; sub line `N% дохода`; legend `🟢 Отложено <amount>` |
| **Overspend** | Add expenses larger than income | Ring fully red; legend `🔴 Перерасход <amount>` in red |

- [ ] **Step 3: Verify add / edit / delete still work**

- Switch the segmented control between Расход and Доход; confirm the correct form is shown.
- Submit each form; confirm the new entry appears in history and totals update.
- Click ✏️ on a row; confirm fields populate; change a value; click Сохранить; confirm the row updates.
- Click 🗑 on a row; confirm the confirmation dialog; confirm the row disappears and totals update.

- [ ] **Step 4: Verify the Chart.js script + canvas are gone**

```bash
grep -n "chart.js\|expenseChart" app/templates/index.html
```
Expected: no matches (the CDN script and the `<canvas id="expenseChart">` should both be removed).

- [ ] **Step 5: Final pytest run**

```bash
python -m pytest -q
```
Expected: all backend tests still pass.

- [ ] **Step 6: Commit (only if any small fix-ups were made during verification; otherwise skip)**

If a typo or small JS fix was needed during verification:
```bash
git add app/templates/index.html app/static/styles.css
git commit -m "Fix-ups from manual verification of redesigned dashboard

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (run after the plan is implemented, before merging)

- [ ] **Spec coverage:** Read the spec at `docs/superpowers/specs/2026-05-27-spent-vs-saved-dashboard-design.md` and confirm every section is implemented:
  - Spent/saved ring with all four states.
  - Per-category bars with amount, %, ranked, stable color.
  - Consistent Russian labels (income type select shows only `label_ru`, no `/ label_uz`).
  - Chart.js + CDN script removed.
  - Number formatting with thousand spaces (`5 200 000`).
  - Segmented Расход/Доход toggle.
  - Backend untouched (no changes outside `app/templates/index.html` and `app/static/styles.css`).

- [ ] **Diff check:** `git diff main --stat` should show only `app/templates/index.html`, `app/static/styles.css`, and the spec/plan/.gitignore from earlier commits. No other files.

- [ ] **Lighthouse sanity (optional):** confirm no broken external requests (Chart.js CDN is gone), and that the page renders correctly at 360px width (Telegram phone width).
