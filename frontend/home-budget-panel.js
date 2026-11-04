const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
  "September", "October", "November", "December"];

const STYLE = `
  :host { display: block; height: 100%; overflow: auto; background: var(--primary-background-color);
    color: var(--primary-text-color); font-family: var(--paper-font-body1_-_font-family, sans-serif); }
  .bar { display: flex; align-items: center; gap: 12px; padding: 12px 16px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, #fff); position: sticky; top: 0; z-index: 2; }
  .bar h1 { font-size: 20px; margin: 0; flex: 1; font-weight: 400; }
  .menu { background: transparent; border: 0; color: inherit; cursor: pointer; font-size: 24px; display: none; }
  .wrap { padding: 16px; max-width: 1200px; margin: 0 auto; }
  .filters { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; }
  input, select, button { font: inherit; padding: 8px 10px; border-radius: 6px;
    border: 1px solid var(--divider-color); background: var(--card-background-color);
    color: var(--primary-text-color); }
  button { cursor: pointer; }
  button.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
  button.danger { color: var(--error-color, #db4437); }
  button.icon { padding: 4px 8px; }
  .summary { display: flex; gap: 24px; flex-wrap: wrap; margin: 8px 0 12px; font-size: 14px; }
  .income { color: var(--success-color, #43a047); }
  .expense { color: var(--error-color, #db4437); }
  .status { margin: 8px 0; padding: 10px 12px; border-radius: 6px; background: var(--secondary-background-color); white-space: pre-line; }
  .status.error { color: var(--error-color, #db4437); }
  .card { background: var(--card-background-color); border-radius: 8px; overflow-x: auto;
    box-shadow: var(--ha-card-box-shadow, none); border: 1px solid var(--divider-color); }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--divider-color); }
  th { color: var(--secondary-text-color); font-weight: 500; }
  td.num, th.num { text-align: right; white-space: nowrap; }
  td.actions { white-space: nowrap; text-align: right; }
  .tag { padding: 2px 8px; border-radius: 10px; background: var(--secondary-background-color); font-size: 12px; }
  .tag.unsorted { background: var(--warning-color, #ffa726); color: #000; }
  .empty { padding: 24px; text-align: center; color: var(--secondary-text-color); }
  dialog { border: 0; border-radius: 12px; padding: 0; min-width: min(420px, 92vw);
    background: var(--card-background-color); color: var(--primary-text-color); }
  dialog::backdrop { background: rgba(0,0,0,.5); }
  form { display: grid; gap: 12px; padding: 20px; }
  form h2 { margin: 0; font-weight: 400; }
  label { display: grid; gap: 4px; font-size: 13px; color: var(--secondary-text-color); }
  label.check { display: flex; align-items: center; gap: 8px; }
  .row { display: flex; justify-content: flex-end; gap: 8px; }
  .tabs { display: flex; gap: 4px; padding: 0 16px; background: var(--app-header-background-color, var(--primary-color));
    position: sticky; top: 56px; z-index: 2; }
  .tab { background: transparent; border: 0; border-bottom: 3px solid transparent; border-radius: 0;
    color: var(--app-header-text-color, #fff); opacity: .75; padding: 10px 16px; }
  .tab.active { opacity: 1; border-bottom-color: currentColor; }
  .grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); margin-bottom: 16px; }
  .kpi { background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px; padding: 12px 14px; }
  .kpi .label { font-size: 12px; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .4px; }
  .kpi .value { font-size: 22px; margin: 4px 0; }
  .kpi .sub { font-size: 12px; color: var(--secondary-text-color); }
  .good { color: var(--success-color, #43a047); }
  .bad { color: var(--error-color, #db4437); }
  .panels { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); margin-bottom: 16px; }
  .panel { background: var(--card-background-color); border: 1px solid var(--divider-color); border-radius: 8px; padding: 14px; min-width: 0; }
  .panel h3 { margin: 0 0 10px; font-size: 15px; font-weight: 500; }
  .bars .line { display: grid; grid-template-columns: minmax(90px, 30%) 1fr auto; gap: 8px; align-items: center;
    padding: 4px 0; font-size: 13px; cursor: pointer; }
  .bars .name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .bars .track { height: 10px; border-radius: 5px; background: var(--secondary-background-color); overflow: hidden; }
  .bars .fill { height: 100%; background: var(--primary-color); border-radius: 5px; }
  .bars .amt { white-space: nowrap; text-align: right; color: var(--secondary-text-color); }
  .chart text { fill: var(--secondary-text-color); font-size: 11px; }
  .chart .col { cursor: pointer; }
  .chart .col:hover rect.hit { fill: var(--secondary-background-color); }
  .alert { padding: 10px 14px; border-radius: 8px; margin-bottom: 16px; background: var(--warning-color, #ffa726); color: #000;
    display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .alert span { flex: 1; }
  .fab { position: fixed; right: 20px; bottom: 20px; width: 56px; height: 56px; border-radius: 50%; font-size: 28px;
    line-height: 1; padding: 0; box-shadow: 0 3px 8px rgba(0,0,0,.35); z-index: 3; }
  @media (max-width: 870px) { .menu { display: block; } }
`;

class HomeBudgetPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._state = { items: [], total: 0, offset: 0, categories: [], used: [], currency: "", unsorted: "Unsorted" };
    this._editing = null;
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._init();
  }

  set narrow(value) { this._narrow = value; }

  async _init() {
    const now = new Date();
    this._month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    this._render();
    try {
      const info = await this._ws({ type: "home_budget/info" });
      Object.assign(this._state, {
        categories: info.categories, currency: info.currency, unsorted: info.unsorted,
        isAdmin: info.is_admin, userId: info.user_id,
      });
      for (const id of ["rules", "import"]) this.shadowRoot.getElementById(id).hidden = !info.is_admin;
      this._fillCategorySelects();
    } catch (err) {
      this._status(err.message || "Failed to load", true);
    }
    this._load(true);
  }

  _ws(msg) { return this._hass.callWS(msg); }

  _status(text, isError = false) {
    const el = this.shadowRoot.getElementById("status");
    el.textContent = text || "";
    el.className = "status" + (isError ? " error" : "");
    el.hidden = !text;
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <div class="bar">
        <button class="menu" id="menu" title="Menu">☰</button>
        <h1>Home Budget</h1>
        <button id="rules">Rules</button>
        <button id="import">Import Revolut</button>
        <button id="add" class="primary">+ Add</button>
        <input type="file" id="file" accept=".csv,.xlsx" hidden>
      </div>
      <div class="tabs">
        <button class="tab active" data-tab="dash">Overview</button>
        <button class="tab" data-tab="tx">Transactions</button>
        <button class="tab" data-tab="rec">Recurring</button>
      </div>
      <div class="wrap" style="padding-bottom:0"><div id="status" class="status" hidden></div></div>
      <div class="wrap" id="recView" hidden>
        <div class="filters">
          <span style="flex:1;color:var(--secondary-text-color);font-size:13px">
            Transactions that are created automatically every month on the chosen day, until the end date.</span>
          <button id="recAdd" class="primary">+ New recurring</button>
        </div>
        <div class="card"><table>
          <thead><tr><th>Description</th><th>Category</th><th>Day</th><th>Period</th><th>Next</th><th>Created</th><th class="num">Amount</th><th></th></tr></thead>
          <tbody id="recRows"></tbody>
        </table></div>
      </div>
      <dialog id="recDialog"><form method="dialog" id="recForm">
        <h2 id="recTitle">Recurring transaction</h2>
        <label>Type<select name="kind"><option value="expense">Expense</option><option value="income">Income</option></select></label>
        <label>Amount<input name="amount" type="number" step="0.01" min="0.01" required></label>
        <label>Day of month<input name="day_of_month" type="number" min="1" max="31" required></label>
        <label>Start date<input name="start_date" type="date" required></label>
        <label>End date (optional)<input name="end_date" type="date"></label>
        <label>Category<input name="category" list="cats" required autocomplete="off"></label>
        <label>Description<input name="description" placeholder="e.g. Loan installment"></label>
        <label>Account<input name="account"></label>
        <label>Currency<input name="currency" maxlength="3"></label>
        <label class="check"><input type="checkbox" name="active" checked><span>Active</span></label>
        <label class="check" id="backfillWrap"><input type="checkbox" name="backfill" checked>
          <span>Add past installments (from the start date up to today)</span></label>
        <div style="color:var(--secondary-text-color);font-size:13px">
          Days after the end of a shorter month use its last day.</div>
        <div class="row"><button type="button" id="recCancel">Cancel</button><button class="primary" type="submit">Save</button></div>
      </form></dialog>
      <div class="wrap" id="dashView">
        <div class="filters">
          <select id="dYear"></select>
          <select id="dMonth"></select>
          <label class="check"><input type="checkbox" id="dTransfers"> Exclude transfers</label>
          <span style="flex:1"></span>
          <button id="addDash" class="primary">+ Add transaction</button>
        </div>
        <div id="dash"><div class="empty">Loading…</div></div>
      </div>
      <button id="fab" class="fab primary" title="Add transaction">+</button>
      <div class="wrap" id="txView" hidden>
        <div class="filters">
          <input type="month" id="month" value="${this._month}">
          <select id="category"></select>
          <select id="kind">
            <option value="">All types</option>
            <option value="expense">Expenses</option>
            <option value="income">Income</option>
          </select>
          <input type="search" id="search" placeholder="Search description / account" style="flex:1;min-width:180px">
          <button id="clear">Clear filters</button>
        </div>
        <div class="summary" id="summary"></div>
        <div class="card"><table>
          <thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Account</th><th>Added by</th><th class="num">Amount</th><th></th></tr></thead>
          <tbody id="rows"></tbody>
        </table></div>
        <div class="row" style="margin-top:12px"><button id="more" hidden>Show more</button></div>
      </div>
      <dialog id="dialog"><form method="dialog" id="form">
        <h2 id="dtitle">Transaction</h2>
        <label>Type<select name="kind"><option value="expense">Expense</option><option value="income">Income</option></select></label>
        <label>Amount<input name="amount" type="number" step="0.01" min="0.01" required></label>
        <label>Date<input name="date" type="date" required></label>
        <label>Category<input name="category" list="cats" required autocomplete="off"></label>
        <datalist id="cats"></datalist>
        <label>Description<input name="description"></label>
        <label>Account<input name="account"></label>
        <label>Currency<input name="currency" maxlength="3"></label>
        <label class="check" id="applyWrap" hidden><input type="checkbox" name="apply_same">
          <span>Remember: always use this category for this description (creates a rule and
          applies it to all matching Unsorted transactions)</span></label>
        <div class="row"><button type="button" id="cancel">Cancel</button><button class="primary" type="submit">Save</button></div>
      </form></dialog>
      <dialog id="rulesDialog"><form method="dialog" id="ruleForm">
        <h2>Categorisation rules</h2>
        <div style="color:var(--secondary-text-color);font-size:13px">
          If a description contains the text, the transaction gets the category. Your rules take
          priority over the built-in defaults.</div>
        <div id="ruleList" style="max-height:40vh;overflow:auto"></div>
        <label>Description contains<input name="pattern" autocomplete="off"></label>
        <label>Category<input name="category" list="cats" autocomplete="off"></label>
        <div id="ruleMsg" style="font-size:13px"></div>
        <div class="row"><button type="button" id="rulesClose">Close</button>
          <button class="primary" type="submit">Add rule</button></div>
      </form></dialog>`;

    const $ = (id) => this.shadowRoot.getElementById(id);
    $("menu").addEventListener("click", () =>
      this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    $("add").addEventListener("click", () => this._openDialog(null));
    $("import").addEventListener("click", () => $("file").click());
    $("file").addEventListener("change", (e) => this._import(e.target));
    $("cancel").addEventListener("click", () => $("dialog").close());
    $("rules").addEventListener("click", () => this._openRules());
    $("rulesClose").addEventListener("click", () => $("rulesDialog").close());
    $("ruleForm").addEventListener("submit", (e) => { e.preventDefault(); this._addRule(); });
    $("ruleList").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-rule]");
      if (btn) this._deleteRule(Number(btn.dataset.rule));
    });
    $("form").addEventListener("submit", (e) => { e.preventDefault(); this._save(); });
    $("more").addEventListener("click", () => this._load(false));
    $("clear").addEventListener("click", () => {
      $("month").value = ""; $("category").value = ""; $("kind").value = ""; $("search").value = "";
      this._load(true);
    });
    for (const id of ["month", "category", "kind"]) $(id).addEventListener("change", () => this._load(true));
    let timer;
    $("search").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => this._load(true), 300); });
    $("rows").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-act]");
      if (!btn) return;
      const item = this._state.items.find((i) => i.id === Number(btn.dataset.id));
      if (!item) return;
      if (btn.dataset.act === "edit") this._openDialog(item);
      else this._delete(item);
    });
    this._fillCategorySelects();

    const now = new Date();
    this._dash = { year: now.getFullYear(), month: now.getMonth() + 1, mode: "month", exclude: false, data: null };
    const years = new Set([now.getFullYear()]);
    $("dYear").innerHTML = [...years].map((y) => `<option value="${y}">${y}</option>`).join("");
    $("dMonth").innerHTML = `<option value="0">Whole year</option>` +
      MONTHS.map((m, i) => `<option value="${i + 1}">${m}</option>`).join("");
    $("dMonth").value = String(this._dash.month);
    $("dYear").addEventListener("change", () => { this._dash.year = Number($("dYear").value); this._loadStats(); });
    $("dMonth").addEventListener("change", () => { this._dash.month = Number($("dMonth").value); this._loadStats(); });
    $("dTransfers").addEventListener("change", () => { this._dash.exclude = $("dTransfers").checked; this._loadStats(); });
    $("recAdd").addEventListener("click", () => this._openRecurring(null));
    $("recCancel").addEventListener("click", () => $("recDialog").close());
    $("recForm").addEventListener("submit", (e) => { e.preventDefault(); this._saveRecurring(); });
    $("recRows").addEventListener("click", (e) => {
      const btn = e.target.closest("button[data-ract]");
      if (!btn) return;
      const item = (this._recurring || []).find((r) => r.id === Number(btn.dataset.id));
      if (!item) return;
      if (btn.dataset.ract === "edit") this._openRecurring(item);
      else this._deleteRecurring(item);
    });
    $("addDash").addEventListener("click", () => this._openDialog(null));
    $("fab").addEventListener("click", () => this._openDialog(null));
    for (const tab of this.shadowRoot.querySelectorAll(".tab")) {
      tab.addEventListener("click", () => this._showTab(tab.dataset.tab));
    }
    $("dash").addEventListener("click", (e) => {
      const el = e.target.closest("[data-cat],[data-m],[data-unsorted]");
      if (!el) return;
      if (el.dataset.m) {
        this._dash.month = Number(el.dataset.m);
        $("dMonth").value = el.dataset.m;
        this._loadStats();
      } else {
        const cat = el.dataset.unsorted ? "Unsorted" : el.dataset.cat;
        const { year, month } = this._dash;
        $("month").value = month ? `${year}-${String(month).padStart(2, "0")}` : "";
        $("category").value = cat;
        $("kind").value = "";
        $("search").value = "";
        this._showTab("tx");
        this._load(true);
      }
    });
    this._loadStats();
  }

  _showTab(name) {
    const $ = (id) => this.shadowRoot.getElementById(id);
    for (const tab of this.shadowRoot.querySelectorAll(".tab")) tab.classList.toggle("active", tab.dataset.tab === name);
    $("dashView").hidden = name !== "dash";
    $("txView").hidden = name !== "tx";
    $("recView").hidden = name !== "rec";
    $("fab").hidden = name === "rec";
    if (name === "rec") this._loadRecurring();
  }

  async _loadRecurring() {
    try {
      const res = await this._ws({ type: "home_budget/recurring" });
      this._recurring = res.items;
      const admin = this._state.isAdmin;
      this.shadowRoot.getElementById("recAdd").hidden = !admin;
      const cur = this._state.currency;
      this.shadowRoot.getElementById("recRows").innerHTML = res.items.length ? res.items.map((r) => {
        const sign = r.kind === "income" ? "+" : "−";
        const period = `${esc(r.start_date)} → ${esc(r.end_date || "no end")}`;
        const next = !r.active ? "paused" : (r.next_date ? esc(r.next_date) : "finished");
        return `<tr>
          <td>${esc(r.description || "—")}</td>
          <td><span class="tag">${esc(r.category)}</span></td>
          <td>${r.day_of_month}</td><td>${period}</td><td>${next}</td><td>${r.generated}×</td>
          <td class="num ${r.kind}">${sign}${esc(r.amount)} ${esc(r.currency || cur)}</td>
          <td class="actions">${admin ? `
            <button class="icon" data-ract="edit" data-id="${r.id}" title="Edit">✎</button>
            <button class="icon danger" data-ract="delete" data-id="${r.id}" title="Delete">🗑</button>` : ""}</td></tr>`;
      }).join("") : `<tr><td colspan="8" class="empty">No recurring transactions</td></tr>`;
    } catch (err) {
      this._status(err.message || "Failed to load recurring transactions", true);
    }
  }

  _openRecurring(item) {
    this._recEditing = item;
    const form = this.shadowRoot.getElementById("recForm");
    form.kind.value = item ? item.kind : "expense";
    form.amount.value = item ? item.amount : "";
    form.day_of_month.value = item ? item.day_of_month : new Date().getDate();
    form.start_date.value = item ? item.start_date : new Date().toISOString().slice(0, 10);
    form.end_date.value = item ? item.end_date || "" : "";
    form.category.value = item ? item.category : "";
    form.description.value = item ? item.description : "";
    form.account.value = item ? item.account : "";
    form.currency.value = item ? item.currency : this._state.currency;
    form.active.checked = item ? !!item.active : true;
    form.backfill.checked = true;
    this.shadowRoot.getElementById("backfillWrap").hidden = !!item;
    this.shadowRoot.getElementById("recTitle").textContent = item ? "Edit recurring transaction" : "New recurring transaction";
    this.shadowRoot.getElementById("recDialog").showModal();
  }

  async _saveRecurring() {
    const form = this.shadowRoot.getElementById("recForm");
    const payload = {
      type: "home_budget/recurring_save", recurring_id: this._recEditing ? this._recEditing.id : null,
      kind: form.kind.value, amount: Number(form.amount.value), day_of_month: Number(form.day_of_month.value),
      start_date: form.start_date.value, end_date: form.end_date.value || "",
      category: form.category.value.trim(), description: form.description.value,
      account: form.account.value, currency: form.currency.value.trim() || this._state.currency,
      active: form.active.checked, backfill: form.backfill.checked,
    };
    try {
      const res = await this._ws(payload);
      this.shadowRoot.getElementById("recDialog").close();
      this._status(res.created ? `${res.created} transaction(s) created.` : "");
      this._loadRecurring();
      this._load(true);
    } catch (err) {
      this._status(err.message || "Save failed", true);
    }
  }

  async _deleteRecurring(item) {
    if (!confirm(`Delete recurring "${item.description || item.category}"? Already created transactions are kept.`)) return;
    try {
      await this._ws({ type: "home_budget/recurring_delete", recurring_id: item.id });
      this._status("");
    } catch (err) {
      this._status(err.message || "Delete failed", true);
    }
    this._loadRecurring();
  }

  async _loadStats() {
    const $ = (id) => this.shadowRoot.getElementById(id);
    if (!$("dash")) return;
    try {
      const d = await this._ws({
        type: "home_budget/stats", year: this._dash.year, month: this._dash.month,
        exclude_transfers: this._dash.exclude,
      });
      this._dash.data = d;
      const years = new Set([...d.years.map(Number).filter(Boolean), new Date().getFullYear(), d.year]);
      $("dYear").innerHTML = [...years].sort((a, b) => b - a)
        .map((y) => `<option value="${y}">${y}</option>`).join("");
      $("dYear").value = String(d.year);
      $("dash").innerHTML = this._dashHtml(d);
    } catch (err) {
      this._status(err.message || "Failed to load statistics", true);
    }
  }

  _dashHtml(d) {
    const cur = esc(d.currency);
    const fmt = (v) => `${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${cur}`;
    const p = d.period, y = d.year_totals;
    const label = d.month ? `${MONTHS[d.month - 1]} ${d.year}` : String(d.year);
    const delta = (now, before, goodWhenDown) => {
      if (!before) return "";
      const pct = ((now - before) / before) * 100;
      const good = goodWhenDown ? pct <= 0 : pct >= 0;
      return `<span class="${good ? "good" : "bad"}">${pct >= 0 ? "▲" : "▼"} ${Math.abs(pct).toFixed(0)}%</span> vs previous`;
    };
    const kpi = (name, value, sub, cls = "") =>
      `<div class="kpi"><div class="label">${name}</div><div class="value ${cls}">${value}</div><div class="sub">${sub || "&nbsp;"}</div></div>`;

    const kpis = [
      kpi(`Expenses · ${label}`, fmt(p.expense), delta(p.expense, p.previous.expense, true), "expense"),
      kpi(`Income · ${label}`, fmt(p.income), delta(p.income, p.previous.income, false), "income"),
      kpi("Balance", fmt(p.balance), p.savings_rate === null ? "" : `Savings rate ${p.savings_rate}%`,
        p.balance >= 0 ? "income" : "expense"),
      kpi("Average per day", fmt(p.average_daily),
        p.projected_expense === null ? `${p.count} transactions` : `Projected: ${fmt(p.projected_expense)}`),
      kpi(`Year to date · ${d.year}`, fmt(y.balance), `Spent ${fmt(y.expense)}`, y.balance >= 0 ? "income" : "expense"),
      kpi("Avg monthly expense", fmt(y.avg_monthly_expense), `Avg income ${fmt(y.avg_monthly_income)}`),
    ].join("");

    const alert = d.unsorted.count
      ? `<div class="alert"><span><b>${d.unsorted.count}</b> unsorted transactions (${fmt(d.unsorted.total)}) need a category.</span>
          <button data-unsorted="1">Review</button></div>` : "";

    const max = Math.max(1, ...d.monthly.flatMap((m) => [m.income, m.expense]));
    const W = 600, H = 200, base = 175, slot = W / 12, bw = 12;
    const cols = d.monthly.map((m, i) => {
      const x = i * slot + slot / 2;
      const he = (m.expense / max) * (base - 10), hi = (m.income / max) * (base - 10);
      const sel = d.month === m.month ? ` fill-opacity=".12"` : ` fill-opacity="0"`;
      return `<g class="col" data-m="${m.month}">
        <title>${MONTHS[i]}: income ${fmt(m.income)}, expenses ${fmt(m.expense)}</title>
        <rect class="hit" x="${i * slot}" y="0" width="${slot}" height="${H}" fill="currentColor"${sel}/>
        <rect x="${x - bw - 1}" y="${base - hi}" width="${bw}" height="${hi}" fill="var(--success-color, #43a047)" rx="2"/>
        <rect x="${x + 1}" y="${base - he}" width="${bw}" height="${he}" fill="var(--error-color, #db4437)" rx="2"/>
        <text x="${x}" y="${H - 6}" text-anchor="middle">${MONTHS[i].slice(0, 3)}</text></g>`;
    }).join("");
    const chart = `<svg class="chart" viewBox="0 0 ${W} ${H}" width="100%" role="img">${cols}</svg>
      <div class="sub" style="font-size:12px;color:var(--secondary-text-color)">
        <span class="income">■</span> Income &nbsp; <span class="expense">■</span> Expenses · click a month</div>`;

    const totalCat = d.categories.reduce((s, c) => s + c.total, 0) || 1;
    const catBars = d.categories.length ? d.categories.slice(0, 12).map((c) => `
      <div class="line" data-cat="${esc(c.category)}" title="${c.n} transactions">
        <span class="name">${esc(c.category)}</span>
        <span class="track"><span class="fill" style="display:block;width:${(c.total / d.categories[0].total) * 100}%"></span></span>
        <span class="amt">${fmt(c.total)} · ${((c.total / totalCat) * 100).toFixed(0)}%</span></div>`).join("")
      : `<div class="empty">No expenses in this period.</div>`;

    const merchants = d.merchants.length ? d.merchants.slice(0, 8).map((m) => `
      <div class="line" style="cursor:default"><span class="name" title="${esc(m.description)}">${esc(m.description)}</span>
        <span></span><span class="amt">${fmt(m.total)} · ${m.n}×</span></div>`).join("")
      : `<div class="empty">No data.</div>`;

    const largest = d.largest.length ? d.largest.map((t) => `
      <div class="line" style="cursor:default"><span class="name" title="${esc(t.description)}">${esc(t.description)}</span>
        <span class="amt" style="text-align:left">${esc(String(t.transaction_date).slice(0, 10))}</span>
        <span class="amt">${fmt(t.amount)}</span></div>`).join("")
      : `<div class="empty">No data.</div>`;

    const dayMax = Math.max(1, ...d.weekdays);
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((n, i) => `
      <div class="line" style="cursor:default"><span class="name">${n}</span>
        <span class="track"><span class="fill" style="display:block;width:${(d.weekdays[i] / dayMax) * 100}%"></span></span>
        <span class="amt">${fmt(d.weekdays[i])}</span></div>`).join("");

    return `${alert}<div class="grid">${kpis}</div>
      <div class="panels">
        <div class="panel"><h3>Income vs expenses · ${d.year}</h3>${chart}</div>
        <div class="panel bars"><h3>Expenses by category · ${label}</h3>${catBars}</div>
        <div class="panel bars"><h3>Top merchants · ${label}</h3>${merchants}</div>
        <div class="panel bars"><h3>Largest expenses · ${label}</h3>${largest}</div>
        <div class="panel bars"><h3>Spending by weekday · ${label}</h3>${days}</div>
      </div>`;
  }

  _allCategories() {
    const set = new Set([...this._state.categories, ...this._state.used]);
    return [...set].sort((a, b) => a.localeCompare(b));
  }

  _fillCategorySelects() {
    const select = this.shadowRoot.getElementById("category");
    if (!select) return;
    const current = select.value;
    select.innerHTML = `<option value="">All categories</option>` +
      this._allCategories().map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
    select.value = current;
    this.shadowRoot.getElementById("cats").innerHTML =
      this._allCategories().map((c) => `<option value="${esc(c)}"></option>`).join("");
  }

  _filters() {
    const $ = (id) => this.shadowRoot.getElementById(id);
    return { month: $("month").value, category: $("category").value, kind: $("kind").value, search: $("search").value.trim() };
  }

  async _load(reset) {
    const pageSize = 100;
    const offset = reset ? 0 : this._state.items.length;
    try {
      const res = await this._ws({ type: "home_budget/list", limit: pageSize, offset, ...this._filters() });
      this._state.items = reset ? res.items : this._state.items.concat(res.items);
      this._state.total = res.total;
      this._state.used = res.used_categories;
      this._state.expenses = res.expenses;
      this._state.income = res.income;
      this._fillCategorySelects();
      this._renderRows();
      if (reset) this._loadStats();
    } catch (err) {
      this._status(err.message || "Failed to load transactions", true);
    }
  }

  _renderRows() {
    const s = this._state;
    const fmt = (n) => `${Number(n).toFixed(2)} ${esc(s.currency)}`;
    this.shadowRoot.getElementById("summary").innerHTML =
      `<span>${s.total} transaction(s)</span>` +
      `<span class="income">Income: ${fmt(s.income || 0)}</span>` +
      `<span class="expense">Expenses: ${fmt(s.expenses || 0)}</span>` +
      `<span>Balance: ${fmt((s.income || 0) - (s.expenses || 0))}</span>`;
    const rows = this.shadowRoot.getElementById("rows");
    if (!s.items.length) {
      rows.innerHTML = `<tr><td colspan="7" class="empty">No transactions</td></tr>`;
    } else {
      rows.innerHTML = s.items.map((i) => {
        const sign = i.kind === "income" ? "+" : "−";
        const unsorted = i.category === s.unsorted ? " unsorted" : "";
        return `<tr>
          <td>${esc(i.transaction_date)}</td>
          <td>${esc(i.description)}</td>
          <td><span class="tag${unsorted}">${esc(i.category)}</span></td>
          <td>${esc(i.account)}</td>
          <td>${esc(i.created_by || "—")}</td>
          <td class="num ${i.kind}">${sign}${esc(i.amount)} ${esc(i.currency)}</td>
          <td class="actions">${s.isAdmin || (i.created_by_id && i.created_by_id === s.userId) ? `
            <button class="icon" data-act="edit" data-id="${i.id}" title="Edit">✎</button>
            <button class="icon danger" data-act="delete" data-id="${i.id}" title="Delete">🗑</button>` : ""}
          </td></tr>`;
      }).join("");
    }
    this.shadowRoot.getElementById("more").hidden = s.items.length >= s.total;
  }

  _openDialog(item) {
    this._editing = item;
    const form = this.shadowRoot.getElementById("form");
    const today = new Date().toISOString().slice(0, 10);
    form.kind.value = item ? item.kind : "expense";
    form.amount.value = item ? item.amount : "";
    form.date.value = item ? item.transaction_date : today;
    form.category.value = item ? item.category : "";
    form.description.value = item ? item.description : "";
    form.account.value = item ? item.account : "";
    form.currency.value = item ? item.currency : this._state.currency;
    form.apply_same.checked = !!item && item.category === this._state.unsorted && this._state.isAdmin;
    this.shadowRoot.getElementById("applyWrap").hidden = !item || !this._state.isAdmin;
    this.shadowRoot.getElementById("dtitle").textContent = item ? "Edit transaction" : "Add transaction";
    this.shadowRoot.getElementById("dialog").showModal();
  }

  async _openRules() {
    this.shadowRoot.getElementById("ruleMsg").textContent = "";
    this.shadowRoot.getElementById("rulesDialog").showModal();
    await this._loadRules();
  }

  async _loadRules() {
    const list = this.shadowRoot.getElementById("ruleList");
    try {
      const { rules } = await this._ws({ type: "home_budget/rules" });
      list.innerHTML = rules.length
        ? `<table><tbody>${rules.map((r) => `<tr><td>${esc(r.pattern)}</td>
            <td><span class="tag">${esc(r.category)}</span></td>
            <td class="actions"><button type="button" class="icon danger" data-rule="${r.id}" title="Delete">🗑</button></td></tr>`).join("")}</tbody></table>`
        : `<div class="empty">No custom rules yet</div>`;
    } catch (err) {
      list.textContent = err.message || "Failed to load rules";
    }
  }

  async _addRule() {
    const form = this.shadowRoot.getElementById("ruleForm");
    const msg = this.shadowRoot.getElementById("ruleMsg");
    try {
      const res = await this._ws({
        type: "home_budget/add_rule", pattern: form.pattern.value, category: form.category.value.trim(),
      });
      msg.textContent = `Rule saved. ${res.applied} Unsorted transaction(s) updated.`;
      form.pattern.value = "";
      await this._loadRules();
      this._load(true);
    } catch (err) {
      msg.textContent = err.message || "Failed to save rule";
    }
  }

  async _deleteRule(id) {
    try {
      await this._ws({ type: "home_budget/delete_rule", rule_id: id });
      await this._loadRules();
    } catch (err) {
      this.shadowRoot.getElementById("ruleMsg").textContent = err.message || "Delete failed";
    }
  }

  async _save() {
    const form = this.shadowRoot.getElementById("form");
    const payload = {
      amount: Number(form.amount.value), kind: form.kind.value, category: form.category.value.trim(),
      date: form.date.value, description: form.description.value, account: form.account.value,
      currency: form.currency.value.trim() || this._state.currency,
    };
    try {
      if (this._editing) {
        const old = this._editing;
        await this._ws({ type: "home_budget/update", transaction_id: old.id, ...payload });
        if (form.apply_same.checked && payload.description.trim() && payload.category !== this._state.unsorted) {
          const res = await this._ws({
            type: "home_budget/recategorize", from_category: old.category,
            to_category: payload.category, description: payload.description, remember: true,
          });
          this._status(`Rule saved. ${res.updated} transaction(s) updated.`);
        } else {
          this._status("");
        }
      } else {
        await this._ws({ type: "home_budget/add", ...payload });
        this._status("");
      }
      this.shadowRoot.getElementById("dialog").close();
      this._load(true);
    } catch (err) {
      this._status(err.message || "Save failed", true);
    }
  }

  async _delete(item) {
    if (!confirm(`Delete "${item.description || item.category}" (${item.amount} ${item.currency})?`)) return;
    try {
      await this._ws({ type: "home_budget/delete", transaction_id: item.id });
      this._status("");
      this._load(true);
    } catch (err) {
      this._status(err.message || "Delete failed", true);
      await this._load(true);
    }
  }

  async _import(input) {
    const file = input.files[0];
    input.value = "";
    if (!file) return;
    this._status(`Importing ${file.name}…`);
    try {
      const content = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(",")[1] || "");
        reader.onerror = () => reject(new Error("Could not read file"));
        reader.readAsDataURL(file);
      });
      const res = await this._ws({ type: "home_budget/import", content, skip_transfers: false });
      let text = `Imported ${res.inserted}, duplicates ${res.duplicates}, skipped ${res.skipped}, errors ${res.errors.length}.`;
      if (res.errors.length) text += "\n" + res.errors.slice(0, 5).join("\n");
      this._status(text, res.errors.length > 0);
      this.shadowRoot.getElementById("category").value = res.inserted ? this._state.unsorted : "";
      this.shadowRoot.getElementById("month").value = "";
      this._load(true);
    } catch (err) {
      this._status(err.message || "Import failed", true);
    }
  }
}

customElements.define("home-budget-panel", HomeBudgetPanel);
