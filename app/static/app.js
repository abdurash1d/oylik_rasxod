// ===== rasxot_bot mini-app =====
(function () {
  "use strict";

  const tg = window.Telegram && window.Telegram.WebApp;
  if (tg) { tg.ready(); tg.expand(); }

  const cfg = window.APP_CONFIG || { apiBase: "/api" };
  const apiBase = cfg.apiBase;
  const { t, getLang, setLang, label } = window.i18n;

  const initDataUnsafe = (tg && tg.initDataUnsafe) || {};
  const user = initDataUnsafe.user || {};
  const headers = {
    "Content-Type": "application/json",
    "X-Telegram-User-Id": user.id || "",
    "X-Telegram-Username": user.username || "",
  };

  // ---- Constants ----
  const CATEGORY_COLORS = {
    food_groceries: "#0071e3", market: "#f59e0b", transportation: "#ff9f0a",
    housing: "#34c759", health: "#ff3b30", shopping: "#af52de",
    personal_care: "#ec4899", utilities: "#06b6d4", miscellaneous: "#94a3b8",
    others: "#64748b",
  };
  const DEFAULT_COLOR = "#64748b";
  const MONTHS = {
    ru: ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
         "август", "сентябрь", "октябрь", "ноябрь", "декабрь"],
    uz: ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
         "avgust", "sentyabr", "oktyabr", "noyabr", "dekabr"],
  };

  // ---- State ----
  let categories = [];
  let incomeTypes = [];
  let editingEntryKey = null;
  let lastSummary = null;
  let lastLedger = [];
  let lastDebts = null;
  let debtsLoaded = false;
  let lastInsights = null;
  let lastTrend = null;
  let insightsLoaded = false;
  let lastSettings = null;
  let modalMode = null; // {kind:'debt',direction} | {kind:'repayment',debtId,person}

  const INSIGHT_ICONS = {
    overspend: "⚠️", savings_rate: "💰", top_category: "📊",
    trend_up: "📈", trend_down: "📉", emergency_fund: "🛟",
    debt_owe: "🔻", debt_lent: "🔺", doing_great: "🎉", no_data: "📭",
    budget_over: "💸",
  };

  // ---- Helpers ----
  const numFmt = new Intl.NumberFormat("ru-RU");
  const fmtAmount = (n) => numFmt.format(n || 0);
  const $ = (id) => document.getElementById(id);

  // Count-up tween for hero numbers; no-op re-render when value is unchanged.
  function animateCount(el, target, format) {
    const prev = el.__countVal || 0;
    if (prev === target) { el.textContent = format(target); el.__countVal = target; return; }
    const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || typeof performance === "undefined") { el.textContent = format(target); el.__countVal = target; return; }
    const start = performance.now();
    const dur = 600;
    function step(now) {
      const p = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = format(Math.round(prev + (target - prev) * eased));
      if (p < 1) requestAnimationFrame(step);
      else el.__countVal = target;
    }
    el.__countVal = prev;
    requestAnimationFrame(step);
  }
  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }
  function fmtDate(iso) {
    if (!iso) return "";
    const p = String(iso).split("-");
    return p.length === 3 ? `${p[2]}.${p[1]}.${p[0]}` : iso;
  }
  function todayIso() { return new Date().toISOString().slice(0, 10); }
  function currentFilters() {
    return { year: Number($("year").value), month: Number($("month").value) };
  }
  function monthName(month) {
    const arr = MONTHS[getLang()] || MONTHS.ru;
    return arr[(month - 1 + 12) % 12] || "";
  }
  function monthShort(month) { return monthName(month).slice(0, 3); }
  function catLabelByKey(key) {
    const c = categories.find((x) => x.key === key);
    return c ? label(c) : key;
  }

  // ---- i18n application ----
  function applyStaticI18n() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.dataset.i18n);
    });
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
      el.setAttribute("placeholder", t(el.dataset.i18nPh));
    });
    $("langToggle").textContent = t("lang_name");
    document.documentElement.lang = getLang();
  }

  function rerenderAll() {
    applyStaticI18n();
    fillCategorySelect();
    fillIncomeSelect();
    if (lastSummary) { renderRing(lastSummary); renderCategoryBars(lastSummary); }
    renderLedgerList(lastLedger);
    if (lastDebts) renderDebts(lastDebts);
    if (lastInsights) renderInsights(lastInsights);
    if (lastTrend) renderTrend(lastTrend);
    renderGreeting();
    updateThemeSeg();
    updateLangSeg();
    if (lastSettings && !$("tab-settings").hidden) fillSettingsForm();
  }

  // ---- Categories / income types ----
  function fillCategorySelect() {
    const select = $("category");
    const prev = select.value;
    select.innerHTML = "";
    for (const c of categories) {
      const opt = document.createElement("option");
      opt.value = c.key;
      opt.textContent = label(c);
      select.appendChild(opt);
    }
    if (prev) select.value = prev;
  }
  function fillIncomeSelect() {
    const select = $("incomeType");
    const prev = select.value;
    select.innerHTML = "";
    for (const it of incomeTypes) {
      const opt = document.createElement("option");
      opt.value = it.key;
      opt.textContent = label(it);
      select.appendChild(opt);
    }
    if (prev) select.value = prev;
  }
  async function loadCategories() {
    try {
      const res = await fetch(`${apiBase}/categories`);
      if (!res.ok) throw new Error();
      categories = (await res.json()).categories || [];
      fillCategorySelect();
    } catch {
      $("formStatus").textContent = t("err_load_categories");
    }
  }
  async function loadIncomeTypes() {
    try {
      const res = await fetch(`${apiBase}/income-types`);
      if (!res.ok) throw new Error();
      incomeTypes = (await res.json()).income_types || [];
      fillIncomeSelect();
    } catch {
      $("incomeFormStatus").textContent = t("err_load_income");
    }
  }

  // ---- Ring ----
  function renderRing(summary) {
    const ring = $("ring");
    const ringAmount = $("ringAmount");
    const ringSub = $("ringSub");
    const legendSaved = $("legendSaved");
    const legendIncome = $("legendIncome");

    const spent = summary.expense_total_uzs || 0;
    const income = summary.income_total_uzs || 0;
    const balance = summary.balance_uzs || 0;
    legendIncome.textContent = fmtAmount(income);
    ring.classList.add("ring-animate");

    if (income === 0 && spent === 0) {
      ring.style.background = "var(--ring-track)";
      animateCount(ringAmount, 0, fmtAmount);
      const name = monthName(currentFilters().month);
      ringSub.textContent = name ? t("ring_no_data", { month: name }) : t("ring_no_data_plain");
      legendSaved.textContent = t("ring_add_first");
      return;
    }
    if (income === 0) {
      ring.style.background = "var(--expense)";
      animateCount(ringAmount, spent, fmtAmount);
      ringSub.textContent = t("ring_no_income");
      legendSaved.textContent = "—";
      return;
    }
    if (spent > income) {
      ring.style.background = "var(--expense)";
      animateCount(ringAmount, spent, fmtAmount);
      ringSub.textContent = t("pct_income", { pct: Math.round((spent / income) * 100) });
      const over = spent - income;
      legendSaved.innerHTML = `<span class="saved-neg">🔴 ${escapeHtml(t("overspend"))} <b>−${fmtAmount(over)}</b></span>`;
      return;
    }
    const pctSpent = Math.round((spent / income) * 100);
    ring.style.background = `conic-gradient(var(--expense) 0 ${pctSpent}%, var(--income) ${pctSpent}% 100%)`;
    ringAmount.textContent = fmtAmount(spent);
    ringSub.textContent = t("pct_income", { pct: pctSpent });
    legendSaved.innerHTML = `<span class="saved-pos">🟢 ${escapeHtml(t("saved"))} <b>${fmtAmount(balance)}</b></span>`;
  }

  // ---- Category bars ----
  function renderCategoryBars(summary) {
    const list = $("categoryList");
    list.innerHTML = "";
    const total = summary.expense_total_uzs || 0;
    const rows = summary.by_category || [];
    if (rows.length === 0) {
      list.innerHTML = `<div class="empty">${escapeHtml(t("no_expenses"))}</div>`;
      return;
    }
    const budgets = (lastSettings && lastSettings.category_budgets) || {};
    for (const row of rows) {
      const pct = total > 0 ? Math.round((row.total_uzs / total) * 100) : 0;
      const color = CATEGORY_COLORS[row.category_key] || DEFAULT_COLOR;
      const catLabel = getLang() === "uz" ? row.category_label_uz : row.category_label_ru;
      const limit = budgets[row.category_key];
      let amountText = `${fmtAmount(row.total_uzs)} · ${pct}%`;
      let over = false;
      if (limit) {
        const bpct = Math.round((row.total_uzs / limit) * 100);
        over = row.total_uzs > limit;
        amountText = `${fmtAmount(row.total_uzs)} / ${fmtAmount(limit)} · ${bpct}%`;
      }
      const wrap = document.createElement("div");
      wrap.className = "cat-row";
      wrap.innerHTML = `
        <div class="cat-meta">
          <span class="cat-name">${escapeHtml(catLabel)}</span>
          <span class="cat-amount${over ? " over" : ""}">${amountText}</span>
        </div>
        <div class="cat-bar"><div class="cat-fill" style="width:${pct}%;background:${color}"></div></div>`;
      list.appendChild(wrap);
    }
  }

  // ---- Summary ----
  async function loadSummary() {
    const { year, month } = currentFilters();
    try {
      const res = await fetch(`${apiBase}/summary/month?year=${year}&month=${month}`, { headers });
      if (!res.ok) throw new Error();
      lastSummary = await res.json();
      renderRing(lastSummary);
      renderCategoryBars(lastSummary);
    } catch {
      $("ledgerStatus").textContent = t("err_load_summary");
    }
  }

  // ---- Ledger ----
  function entryTypeLabel(type) { return type === "income" ? t("entry_income") : t("entry_expense"); }
  function renderLedgerRow(entry) {
    const key = `${entry.entry_type}:${entry.id}`;
    const isEdit = editingEntryKey === key;
    const isIncome = entry.entry_type === "income";
    const rowLabel = getLang() === "uz" ? entry.label_uz : entry.label_ru;

    if (!isEdit) {
      const amountClass = isIncome ? "amount income" : "amount expense";
      const sign = isIncome ? "+" : "−";
      return `
        <div class="ledger-row">
          <div class="ledger-main">
            <span class="badge ${isIncome ? "income" : "expense"}">${escapeHtml(entryTypeLabel(entry.entry_type))}</span>
            <strong>${escapeHtml(rowLabel)}</strong>
            <span class="ledger-date">${escapeHtml(fmtDate(entry.date))}</span>
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
        </div>`;
    }
    const options = isIncome ? incomeTypes : categories;
    const optionsHtml = options
      .map((o) => `<option value="${o.key}" ${o.key === entry.raw_key ? "selected" : ""}>${escapeHtml(label(o))}</option>`)
      .join("");
    return `
      <div class="ledger-row editing">
        <div class="ledger-edit">
          <select id="editRawKey">${optionsHtml}</select>
          <input id="editAmount" type="number" min="1" step="1" value="${escapeHtml(String(entry.amount_uzs))}" />
          <input id="editDate" type="date" value="${escapeHtml(entry.date)}" />
          <input id="editNote" type="text" maxlength="1024" value="${escapeHtml(entry.note || "")}" placeholder="${escapeHtml(t("f_note"))}" />
        </div>
        <div class="ledger-actions">
          <button type="button" class="mini success" data-action="save-edit"
                  data-entry-key="${key}" data-entry-type="${entry.entry_type}" data-entry-id="${entry.id}">${escapeHtml(t("save"))}</button>
          <button type="button" class="mini" data-action="cancel-edit">${escapeHtml(t("cancel"))}</button>
        </div>
      </div>`;
  }
  function renderLedgerList(entries) {
    const list = $("ledgerList");
    list.innerHTML = (entries && entries.length)
      ? entries.map(renderLedgerRow).join("")
      : `<div class="empty">${escapeHtml(t("no_records"))}</div>`;
  }
  async function loadLedger() {
    const { year, month } = currentFilters();
    try {
      const res = await fetch(`${apiBase}/ledger/month?year=${year}&month=${month}`, { headers });
      if (!res.ok) throw new Error();
      lastLedger = (await res.json()).entries || [];
      renderLedgerList(lastLedger);
    } catch {
      $("ledgerList").innerHTML = `<div class="empty">${escapeHtml(t("err_load_history"))}</div>`;
    }
  }

  async function refreshReport() {
    await Promise.all([loadSummary(), loadLedger()]);
    refreshInsightsIfLoaded();
  }

  // Single round-trip for everything the first paint of the report needs.
  async function loadBootstrap() {
    const { year, month } = currentFilters();
    try {
      const res = await fetch(`${apiBase}/bootstrap?year=${year}&month=${month}`, { headers });
      if (!res.ok) throw new Error();
      const d = await res.json();
      categories = d.categories || []; fillCategorySelect();
      incomeTypes = d.income_types || []; fillIncomeSelect();
      lastSettings = d.settings || null; renderGreeting();
      lastSummary = d.summary; renderRing(lastSummary); renderCategoryBars(lastSummary);
      lastLedger = d.ledger || []; renderLedgerList(lastLedger);
    } catch {
      // Fallback to individual loaders if bootstrap is unavailable.
      Promise.all([loadCategories(), loadIncomeTypes()]).then(() => loadLedger());
      loadSummary();
      loadSettings();
    }
  }

  // ---- Debts ----
  function debtCardHtml(d) {
    const isLent = d.direction === "lent";
    const amountClass = isLent ? "pos" : "neg";
    const reps = d.repayments || [];
    const repHtml = reps.map((r) => `
      <div class="repayment-row">
        <span>−${fmtAmount(r.amount_uzs)} · ${escapeHtml(fmtDate(r.repayment_date))}</span>
        <button type="button" class="mini danger" data-action="del-repayment"
                data-debt-id="${d.id}" data-repayment-id="${r.id}">🗑</button>
      </div>`).join("");
    const historyHtml = reps.length
      ? `<details class="debt-history"><summary>${escapeHtml(t("add_repayment"))} · ${reps.length}</summary>${repHtml}</details>`
      : "";
    const statusHtml = d.settled
      ? `<span class="debt-badge settled">${escapeHtml(t("settled_badge"))}</span>`
      : `<span class="debt-remain">${escapeHtml(t("debt_outstanding"))} ${fmtAmount(d.outstanding_uzs)}</span>`;
    const actionsHtml = d.settled ? "" : `
      <button type="button" class="mini" data-action="add-repayment" data-debt-id="${d.id}" data-person="${escapeHtml(d.counterparty)}">+ ${escapeHtml(t("add_repayment"))}</button>
      <button type="button" class="mini success" data-action="settle" data-debt-id="${d.id}">${escapeHtml(t("settle"))}</button>`;
    return `
      <div class="debt-card ${d.settled ? "is-settled" : ""}">
        <div class="debt-head">
          <span class="debt-name">${escapeHtml(d.counterparty)}</span>
          <span class="debt-amount ${amountClass}">${fmtAmount(d.outstanding_uzs)}</span>
        </div>
        <div class="debt-meta">
          <span>${fmtAmount(d.principal_amount_uzs)} · ${escapeHtml(fmtDate(d.debt_date))}${d.note ? " · " + escapeHtml(d.note) : ""}</span>
          ${statusHtml}
        </div>
        ${historyHtml}
        <div class="debt-card-actions">
          ${actionsHtml}
          <button type="button" class="mini danger" data-action="del-debt" data-debt-id="${d.id}">🗑</button>
        </div>
      </div>`;
  }
  function renderDebts(data) {
    const totals = data.totals || { lent_outstanding: 0, borrowed_outstanding: 0, net: 0 };
    const netEl = $("debtNet");
    animateCount(netEl, totals.net, (v) => (v >= 0 ? "+" : "−") + fmtAmount(Math.abs(v)));
    netEl.className = "debt-net-value " + (totals.net >= 0 ? "pos" : totals.net < 0 ? "neg" : "");
    $("debtLentTotal").textContent = fmtAmount(totals.lent_outstanding);
    $("debtBorrowedTotal").textContent = fmtAmount(totals.borrowed_outstanding);

    const debts = data.debts || [];
    const lent = debts.filter((d) => d.direction === "lent");
    const borrowed = debts.filter((d) => d.direction === "borrowed");
    $("debtListLent").innerHTML = lent.length
      ? lent.map(debtCardHtml).join("")
      : `<div class="empty">${escapeHtml(t("no_debts_lent"))}</div>`;
    $("debtListBorrowed").innerHTML = borrowed.length
      ? borrowed.map(debtCardHtml).join("")
      : `<div class="empty">${escapeHtml(t("no_debts_borrowed"))}</div>`;
  }
  async function loadDebts() {
    try {
      const res = await fetch(`${apiBase}/debts`, { headers });
      if (!res.ok) throw new Error();
      lastDebts = await res.json();
      debtsLoaded = true;
      $("debtStatus").textContent = "";
      renderDebts(lastDebts);
    } catch {
      $("debtStatus").textContent = t("err_load_debts");
    }
  }

  // ---- Insights / analytics ----
  function insightContent(i) {
    const p = i.params || {};
    const tp = {};
    // Amount-like params are formatted; {target} as a percent (e.g. 20) also
    // formats safely through fmtAmount.
    ["over", "saved", "amount", "target"].forEach((k) => { if (p[k] != null) tp[k] = fmtAmount(p[k]); });
    if (p.pct != null) tp.pct = p.pct;
    if (p.months != null) tp.months = p.months;
    if (p.category_key != null) tp.label = catLabelByKey(p.category_key);
    return {
      icon: INSIGHT_ICONS[i.code] || "•",
      title: t("ins_" + i.code + "_title", tp),
      msg: t("ins_" + i.code + "_msg", tp),
    };
  }
  function renderSavingsHero(data) {
    const el = $("savingsRate");
    const verdict = $("savingsVerdict");
    if (data.savings_level === "none") {
      el.textContent = "—";
      el.className = "savings-rate";
    } else {
      el.textContent = data.savings_rate_pct + "%";
      const cls = data.savings_level === "good" ? "good" : data.savings_level === "ok" ? "ok" : "low";
      el.className = "savings-rate " + cls;
    }
    verdict.textContent = t("savings_" + data.savings_level);
  }
  function renderInsights(data) {
    renderSavingsHero(data);
    const list = $("insightList");
    list.innerHTML = "";
    for (const i of data.insights || []) {
      const c = insightContent(i);
      const card = document.createElement("div");
      card.className = "insight-card sev-" + i.severity;
      card.innerHTML = `
        <div class="insight-icon">${c.icon}</div>
        <div class="insight-body">
          <div class="insight-title">${escapeHtml(c.title)}</div>
          <div class="insight-msg">${escapeHtml(c.msg)}</div>
        </div>`;
      list.appendChild(card);
    }
  }
  function renderTrend(data) {
    const wrap = $("trendChart");
    const months = data.months || [];
    const max = Math.max(1, ...months.map((m) => Math.max(m.income_total_uzs, m.expense_total_uzs)));
    const cols = months.map((m) => {
      const incH = Math.round((m.income_total_uzs / max) * 100);
      const expH = Math.round((m.expense_total_uzs / max) * 100);
      return `
        <div class="trend-col">
          <div class="trend-bars">
            <div class="trend-bar inc" style="height:${incH}%" title="${fmtAmount(m.income_total_uzs)}"></div>
            <div class="trend-bar exp" style="height:${expH}%" title="${fmtAmount(m.expense_total_uzs)}"></div>
          </div>
          <div class="trend-label">${escapeHtml(monthShort(m.month))}</div>
        </div>`;
    }).join("");
    wrap.innerHTML = `
      <div class="trend-cols">${cols}</div>
      <div class="trend-legend">
        <span><i class="dot inc"></i>${escapeHtml(t("income"))}</span>
        <span><i class="dot exp"></i>${escapeHtml(t("seg_expense"))}</span>
      </div>`;
  }
  async function loadInsights() {
    const { year, month } = currentFilters();
    try {
      const res = await fetch(`${apiBase}/insights?year=${year}&month=${month}`, { headers });
      if (!res.ok) throw new Error();
      lastInsights = await res.json();
      insightsLoaded = true;
      $("insightStatus").textContent = "";
      renderInsights(lastInsights);
    } catch {
      $("insightStatus").textContent = t("err_load_insights");
    }
  }
  async function loadTrend() {
    const { year, month } = currentFilters();
    try {
      const res = await fetch(`${apiBase}/stats/trend?year=${year}&month=${month}&months=6`, { headers });
      if (!res.ok) throw new Error();
      lastTrend = await res.json();
      renderTrend(lastTrend);
    } catch {
      /* trend is secondary; leave previous render in place */
    }
  }
  function refreshInsightsIfLoaded() {
    if (insightsLoaded) { loadInsights(); loadTrend(); }
  }

  // ---- Modal ----
  function openModal(mode) {
    modalMode = mode;
    const personRow = $("modalPerson").closest("label");
    const amountLabel = $("modalAmountLabel");
    $("modalStatus").textContent = "";
    $("modalForm").reset();
    $("modalDate").value = todayIso();

    if (mode.kind === "debt") {
      $("modalTitle").textContent = mode.direction === "lent" ? t("add_lent") : t("add_borrowed");
      personRow.hidden = false;
      $("modalPerson").required = true;
      amountLabel.textContent = t("f_amount");
    } else {
      $("modalTitle").textContent = `${t("add_repayment")} · ${mode.person}`;
      personRow.hidden = true;
      $("modalPerson").required = false;
      amountLabel.textContent = t("repayment_amount");
    }
    $("modal").hidden = false;
  }
  function closeModal() { $("modal").hidden = true; modalMode = null; }

  async function submitModal(e) {
    e.preventDefault();
    if (!modalMode) return;
    const status = $("modalStatus");
    status.textContent = "";
    const amount = Number($("modalAmount").value);
    const dateVal = $("modalDate").value;
    const noteVal = $("modalNote").value || null;

    try {
      let res;
      if (modalMode.kind === "debt") {
        res = await fetch(`${apiBase}/debts`, {
          method: "POST", headers,
          body: JSON.stringify({
            counterparty: $("modalPerson").value.trim(),
            direction: modalMode.direction,
            principal_amount_uzs: amount,
            debt_date: dateVal,
            note: noteVal,
          }),
        });
      } else {
        res = await fetch(`${apiBase}/debts/${modalMode.debtId}/repayments`, {
          method: "POST", headers,
          body: JSON.stringify({ amount_uzs: amount, repayment_date: dateVal, note: noteVal }),
        });
      }
      if (!res.ok) {
        status.textContent = res.status === 400 ? t("err_repayment") : t("err_save_debt");
        return;
      }
      lastDebts = await res.json();
      renderDebts(lastDebts);
      closeModal();
    } catch {
      status.textContent = t("err_save_debt");
    }
  }

  async function debtAction(action, btn) {
    const debtId = btn.dataset.debtId;
    const status = $("debtStatus");
    status.textContent = "";
    try {
      if (action === "add-repayment") {
        openModal({ kind: "repayment", debtId, person: btn.dataset.person });
        return;
      }
      if (action === "settle") {
        const res = await fetch(`${apiBase}/debts/${debtId}/settle`, { method: "POST", headers });
        if (!res.ok) throw new Error();
        lastDebts = await res.json();
        renderDebts(lastDebts);
        return;
      }
      if (action === "del-debt") {
        if (!confirm(t("confirm_delete_debt"))) return;
        const res = await fetch(`${apiBase}/debts/${debtId}`, { method: "DELETE", headers });
        if (!res.ok) throw new Error();
        await loadDebts();
        return;
      }
      if (action === "del-repayment") {
        if (!confirm(t("confirm_delete_repayment"))) return;
        const repaymentId = btn.dataset.repaymentId;
        const res = await fetch(`${apiBase}/debts/${debtId}/repayments/${repaymentId}`, { method: "DELETE", headers });
        if (!res.ok) throw new Error();
        await loadDebts();
        return;
      }
    } catch {
      status.textContent = t("err_load_debts");
    }
  }

  // ---- Setup ----
  function setupTabs() {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        document.querySelectorAll(".tab-btn").forEach((b) => {
          const on = b === btn;
          b.classList.toggle("active", on);
          b.setAttribute("aria-selected", on ? "true" : "false");
        });
        $("tab-report").hidden = tab !== "report";
        $("tab-insights").hidden = tab !== "insights";
        $("tab-debts").hidden = tab !== "debts";
        $("tab-settings").hidden = true;
        $("settingsBtn").classList.remove("active");
        if (tab === "debts" && !debtsLoaded) loadDebts();
        if (tab === "insights") { loadInsights(); loadTrend(); }
      });
    });
  }

  function setupLangToggle() {
    $("langToggle").addEventListener("click", () => {
      setLang(getLang() === "ru" ? "uz" : "ru");
      rerenderAll();
    });
  }

  // ---- Theme (light / dark) ----
  function effectiveTheme() {
    const forced = document.documentElement.getAttribute("data-theme");
    if (forced === "dark" || forced === "light") return forced;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark" : "light";
  }
  function syncThemeIcon() {
    // Show the icon representing the current mode: moon in dark, sun in light.
    $("themeToggle").textContent = effectiveTheme() === "dark" ? "☾" : "☀";
    if (document.getElementById("themeSeg")) updateThemeSeg();
  }
  function setupThemeToggle() {
    syncThemeIcon();
    $("themeToggle").addEventListener("click", () => {
      const next = effectiveTheme() === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try { localStorage.setItem("theme", next); } catch (e) {}
      syncThemeIcon();
    });
    // Keep the icon in sync if the system theme changes while in auto mode.
    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
        if (!document.documentElement.getAttribute("data-theme")) syncThemeIcon();
      });
    }
  }

  function setupSegmented() {
    const segBtns = document.querySelectorAll(".seg-btn");
    segBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        segBtns.forEach((b) => {
          b.classList.toggle("active", b === btn);
          b.setAttribute("aria-selected", b === btn ? "true" : "false");
        });
        const tab = btn.dataset.tab;
        $("expenseForm").classList.toggle("hidden", tab !== "expense");
        $("incomeForm").classList.toggle("hidden", tab !== "income");
      });
    });
  }

  function setupForms() {
    $("expenseForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const status = $("formStatus");
      status.textContent = "";
      const payload = {
        category_key: $("category").value,
        amount_uzs: Number($("amount").value),
        expense_date: $("expenseDate").value,
        note: $("note").value || null,
      };
      try {
        const res = await fetch(`${apiBase}/expenses`, { method: "POST", headers, body: JSON.stringify(payload) });
        if (!res.ok) throw new Error();
        status.textContent = t("saved_ok");
        $("amount").value = ""; $("note").value = "";
        await refreshReport();
      } catch { status.textContent = t("err_save_expense"); }
    });
    $("incomeForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      const status = $("incomeFormStatus");
      status.textContent = "";
      const payload = {
        income_type_key: $("incomeType").value,
        amount_uzs: Number($("incomeAmount").value),
        income_date: $("incomeDate").value,
        note: $("incomeNote").value || null,
      };
      try {
        const res = await fetch(`${apiBase}/incomes`, { method: "POST", headers, body: JSON.stringify(payload) });
        if (!res.ok) throw new Error();
        status.textContent = t("saved_ok");
        $("incomeAmount").value = ""; $("incomeNote").value = "";
        await refreshReport();
      } catch { status.textContent = t("err_save_income"); }
    });
  }

  function setupReload() {
    $("reloadBtn").addEventListener("click", () => refreshReport());
    let timer = null;
    const debounced = () => { clearTimeout(timer); timer = setTimeout(() => refreshReport(), 350); };
    $("year").addEventListener("change", debounced);
    $("month").addEventListener("change", debounced);
  }

  function setupLedgerActions() {
    $("ledgerList").addEventListener("click", async (e) => {
      const btn = e.target.closest("button[data-action]");
      if (!btn) return;
      const action = btn.dataset.action;
      const status = $("ledgerStatus");
      status.textContent = "";

      if (action === "start-edit") { editingEntryKey = btn.dataset.entryKey; await loadLedger(); return; }
      if (action === "cancel-edit") { editingEntryKey = null; await loadLedger(); return; }
      if (action === "delete") {
        if (!confirm(t("confirm_delete"))) return;
        const endpoint = btn.dataset.entryType === "income" ? "incomes" : "expenses";
        try {
          const res = await fetch(`${apiBase}/${endpoint}/${btn.dataset.entryId}`, { method: "DELETE", headers });
          if (!res.ok) throw new Error();
          editingEntryKey = null; status.textContent = t("deleted");
          await refreshReport();
        } catch { status.textContent = t("err_delete"); }
        return;
      }
      if (action === "save-edit") {
        const entryType = btn.dataset.entryType;
        const endpoint = entryType === "income" ? "incomes" : "expenses";
        const rawKey = $("editRawKey").value;
        const amount = Number($("editAmount").value);
        const dateVal = $("editDate").value;
        const noteVal = $("editNote").value || null;
        const payload = entryType === "income"
          ? { income_type_key: rawKey, amount_uzs: amount, income_date: dateVal, note: noteVal }
          : { category_key: rawKey, amount_uzs: amount, expense_date: dateVal, note: noteVal };
        try {
          const res = await fetch(`${apiBase}/${endpoint}/${btn.dataset.entryId}`, { method: "PATCH", headers, body: JSON.stringify(payload) });
          if (!res.ok) throw new Error();
          editingEntryKey = null; status.textContent = t("saved_ok");
          await refreshReport();
        } catch { status.textContent = t("err_save_changes"); }
        return;
      }
    });
  }

  function setupDebts() {
    $("addLentBtn").addEventListener("click", () => openModal({ kind: "debt", direction: "lent" }));
    $("addBorrowedBtn").addEventListener("click", () => openModal({ kind: "debt", direction: "borrowed" }));
    $("tab-debts").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-action]");
      if (!btn) return;
      debtAction(btn.dataset.action, btn);
    });
  }

  function setupModal() {
    $("modalForm").addEventListener("submit", submitModal);
    $("modal").addEventListener("click", (e) => {
      if (e.target.closest('[data-action="modal-close"]')) closeModal();
    });
  }

  // ---- Settings ----
  function renderGreeting() {
    const el = $("greeting");
    const name = lastSettings && lastSettings.display_name;
    if (name) { el.textContent = t("greeting", { name }); el.hidden = false; }
    else { el.textContent = ""; el.hidden = true; }
  }
  function currentThemeMode() {
    return (function () { try { return localStorage.getItem("theme"); } catch (e) { return null; } })() || "system";
  }
  function updateThemeSeg() {
    const mode = currentThemeMode();
    document.querySelectorAll("#themeSeg button").forEach((b) => b.classList.toggle("active", b.dataset.themeMode === mode));
  }
  function updateLangSeg() {
    document.querySelectorAll("#langSeg button").forEach((b) => b.classList.toggle("active", b.dataset.langMode === getLang()));
  }
  function setThemeMode(mode) {
    if (mode === "system") {
      document.documentElement.removeAttribute("data-theme");
      try { localStorage.removeItem("theme"); } catch (e) {}
    } else {
      document.documentElement.setAttribute("data-theme", mode);
      try { localStorage.setItem("theme", mode); } catch (e) {}
    }
    syncThemeIcon();
    updateThemeSeg();
  }
  function buildBudgetList() {
    const list = $("budgetList");
    list.innerHTML = "";
    const budgets = (lastSettings && lastSettings.category_budgets) || {};
    for (const c of categories) {
      const row = document.createElement("label");
      row.className = "budget-row";
      row.innerHTML = `
        <span>${escapeHtml(label(c))}</span>
        <input type="number" min="0" step="1000" data-cat="${c.key}" value="${budgets[c.key] || ""}" placeholder="0" />`;
      list.appendChild(row);
    }
  }
  function fillSettingsForm() {
    if (!lastSettings) return;
    $("setName").value = lastSettings.display_name || "";
    $("setAbout").value = lastSettings.about || "";
    $("setSavings").value = lastSettings.savings_target_pct;
    $("setEmergency").value = lastSettings.emergency_months;
    buildBudgetList();
    updateThemeSeg();
    updateLangSeg();
  }
  async function loadSettings() {
    try {
      const res = await fetch(`${apiBase}/settings`, { headers });
      if (!res.ok) throw new Error();
      lastSettings = await res.json();
      renderGreeting();
      if (lastSummary) renderCategoryBars(lastSummary);
    } catch {
      /* settings are optional; ignore quietly */
    }
  }
  async function saveSettings() {
    const status = $("settingsStatus");
    status.textContent = "";
    const budgets = {};
    document.querySelectorAll("#budgetList input[data-cat]").forEach((inp) => {
      const v = Number(inp.value);
      if (v > 0) budgets[inp.dataset.cat] = Math.round(v);
    });
    const payload = {
      display_name: $("setName").value || null,
      about: $("setAbout").value || null,
      savings_target_pct: Number($("setSavings").value),
      emergency_months: Number($("setEmergency").value),
      category_budgets: budgets,
    };
    try {
      const res = await fetch(`${apiBase}/settings`, { method: "PUT", headers, body: JSON.stringify(payload) });
      if (!res.ok) throw new Error();
      lastSettings = await res.json();
      status.textContent = t("settings_saved");
      renderGreeting();
      refreshReport();
    } catch {
      status.textContent = t("err_save_settings");
    }
  }
  async function openSettings() {
    ["report", "insights", "debts"].forEach((p) => { $("tab-" + p).hidden = true; });
    document.querySelectorAll(".tab-btn").forEach((b) => { b.classList.remove("active"); b.setAttribute("aria-selected", "false"); });
    $("tab-settings").hidden = false;
    $("settingsBtn").classList.add("active");
    if (!lastSettings) await loadSettings();
    fillSettingsForm();
  }
  function setupSettings() {
    $("settingsBtn").addEventListener("click", openSettings);
    $("saveSettingsBtn").addEventListener("click", saveSettings);
    $("themeSeg").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-theme-mode]");
      if (b) setThemeMode(b.dataset.themeMode);
    });
    $("langSeg").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-lang-mode]");
      if (b && b.dataset.langMode !== getLang()) { setLang(b.dataset.langMode); rerenderAll(); }
    });
  }

  // ---- Init ----
  (function init() {
    applyStaticI18n();
    const today = todayIso();
    $("expenseDate").value = today;
    $("incomeDate").value = today;

    setupTabs();
    setupLangToggle();
    setupThemeToggle();
    setupSegmented();
    setupForms();
    setupReload();
    setupLedgerActions();
    setupDebts();
    setupModal();
    setupSettings();

    loadBootstrap();
  })();
})();
