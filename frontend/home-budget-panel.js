const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));

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
      Object.assign(this._state, { categories: info.categories, currency: info.currency, unsorted: info.unsorted });
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
      <div class="wrap">
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
        <div id="status" class="status" hidden></div>
        <div class="summary" id="summary"></div>
        <div class="card"><table>
          <thead><tr><th>Date</th><th>Description</th><th>Category</th><th>Account</th><th class="num">Amount</th><th></th></tr></thead>
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
      rows.innerHTML = `<tr><td colspan="6" class="empty">No transactions</td></tr>`;
    } else {
      rows.innerHTML = s.items.map((i) => {
        const sign = i.kind === "income" ? "+" : "−";
        const unsorted = i.category === s.unsorted ? " unsorted" : "";
        return `<tr>
          <td>${esc(i.transaction_date)}</td>
          <td>${esc(i.description)}</td>
          <td><span class="tag${unsorted}">${esc(i.category)}</span></td>
          <td>${esc(i.account)}</td>
          <td class="num ${i.kind}">${sign}${esc(i.amount)} ${esc(i.currency)}</td>
          <td class="actions">
            <button class="icon" data-act="edit" data-id="${i.id}" title="Edit">✎</button>
            <button class="icon danger" data-act="delete" data-id="${i.id}" title="Delete">🗑</button>
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
    form.apply_same.checked = !!item && item.category === this._state.unsorted;
    this.shadowRoot.getElementById("applyWrap").hidden = !item;
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
